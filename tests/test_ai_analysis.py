"""Stage 3 AI analysis: switch, SAR safety, firm isolation, drafts, client blindness.

Synthetic text only. A fake model is injected everywhere: no network, no key, no real model.
"""

import io
import json
from pathlib import Path

import httpx
import pytest
from reportlab.pdfgen import canvas
from sqlalchemy import select

from ai_adapter.schemas import AnalyzeOutput, AnalyzeRequest
from ai_adapter.schemas import Finding as ModelFinding
from app.api.ai_analysis import get_document_reader, get_model_client
from app.config import Settings, get_settings
from app.database.models import (
    AiDraft,
    AuditLog,
    Document,
    DocumentItemLink,
    Engagement,
    Finding,
    ResponseRequest,
)
from audit_engine.engine import DEFAULT_MODELS, MAX_DOCUMENTS
from audit_engine.model_client import HttpAdapterClient, ModelRefused
from audit_engine.rubric import RUBRIC_PATH, rubric_for, rubric_items
from tests.test_backend_api import backend, sign_in_auditor, sign_in_client  # noqa: F401

BODY_MARK = "SYNTHETIC-EVIDENCE-BODY-5e1"
DRAFT_MARK = "AI-DRAFT-MARKER-5e2"


class FakeModel:
    """Returns one finding on page 1 of whatever document it is given."""

    def __init__(self, findings=None, error=None):
        self.requests: list[AnalyzeRequest] = []
        self.models: list[str] = []
        self.findings = findings
        self.error = error

    def analyze(self, req: AnalyzeRequest, model_id: str) -> AnalyzeOutput:
        self.requests.append(req)
        self.models.append(model_id)
        if self.error:
            raise ModelRefused(self.error)
        if self.findings is not None:
            return AnalyzeOutput(findings=[f(req) for f in self.findings])
        return AnalyzeOutput(
            findings=[
                ModelFinding(
                    document_id=req.document_id,
                    page=1,
                    kind="finding",
                    title="Gap",
                    issue=DRAFT_MARK,
                ),
                ModelFinding(
                    document_id=req.document_id,
                    page=1,
                    kind="client_request",
                    title="Ask",
                    issue="Please share the sign-off dates.",
                ),
            ]
        )


def pdf_bytes(*pages: str) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    for text in pages:
        pdf.drawString(72, 720, text)
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


@pytest.fixture
def ai(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    store: dict[str, bytes | None] = {}
    reads: list[str] = []
    model = FakeModel()

    def reader(document):
        reads.append(document.id)
        return store.get(document.id)

    settings = Settings(
        _env_file=None,
        database_url="sqlite+pysqlite:///:memory:",
        session_secret="synthetic-test-session-secret-at-least-32-bytes",
        cors_origins="http://localhost:3000",
        ai_analysis_enabled=True,
    )
    client.app.dependency_overrides[get_settings] = lambda: settings
    client.app.dependency_overrides[get_document_reader] = lambda: reader
    client.app.dependency_overrides[get_model_client] = lambda: model

    def add_document(name, content, *, engagement="engagement_a", firm="firm_a", item="item_a"):
        with factory() as db:
            doc = Document(
                firm_id=ids[firm],
                engagement_id=ids[engagement],
                item_instance_id=ids[item] if item else None,
                uploaded_by_id=ids["client_a"],
                original_name=name,
                size_bytes=len(content or b""),
                egnyte_path=f"s3://synthetic/firms/{ids[firm]}/{name}",
                sha256="e" * 64,
                number=f"9.{len(store) + 1}",
            )
            db.add(doc)
            db.commit()
            store[doc.id] = content
            return doc.id

    return client, factory, ids, model, add_document, reads, settings


def url(ids, tail="", engagement="engagement_a"):
    return f"/auditor/engagements/{ids[engagement]}/ai-analysis{tail}"


# --- switch ---------------------------------------------------------------------------


def test_switch_defaults_to_off():
    assert Settings(_env_file=None).ai_analysis_enabled is False


def test_every_ai_route_is_404_when_the_switch_is_off(ai):
    client, factory, ids, model, add, reads, settings = ai
    doc = add("a.txt", b"hello")
    client.app.dependency_overrides[get_settings] = lambda: settings.model_copy(
        update={"ai_analysis_enabled": False}
    )
    sign_in_auditor(client)
    assert client.get(url(ids)).status_code == 404
    assert client.post(url(ids, "/run")).status_code == 404
    for call in (
        client.put("/auditor/ai-drafts/x", json={"title": "t", "body": "b"}),
        client.post("/auditor/ai-drafts/x/accept"),
        client.post("/auditor/ai-drafts/x/reject"),
    ):
        assert call.status_code == 404
    assert model.requests == [] and reads == [] and doc


def test_client_gets_403_not_404_on_ai_routes_even_when_off(ai):
    client, _, ids, *_ = ai
    sign_in_client(client)
    assert client.get(url(ids)).status_code == 403
    assert client.post(url(ids, "/run")).status_code == 403


# --- run, drafts ----------------------------------------------------------------------


def test_run_returns_pending_drafts_that_cite_document_and_page(ai):
    client, factory, ids, model, add, *_ = ai
    doc = add("alerts.txt", BODY_MARK.encode())
    sign_in_auditor(client)
    body = client.post(url(ids, "/run")).json()
    assert body["lastRun"]["documentsAnalyzed"] == 1
    assert body["lastRun"]["models"] == [DEFAULT_MODELS[0]]
    assert {d["kind"] for d in body["drafts"]} == {"finding", "client_request"}
    for draft in body["drafts"]:
        assert draft["status"] == "pending" and draft["documentId"] == doc
        assert draft["documentName"] == "alerts.txt" and draft["page"] == 1
    request = model.requests[0]
    assert request.prompt_version == "v2" and request.source == "synthetic"
    assert request.firm_id == ids["firm_a"] and request.engagement_id == ids["engagement_a"]
    assert request.user_id == ids["auditor"]
    assert request.rubric == rubric_for("AML-BD-004") and request.rubric
    with factory() as db:  # nothing reached the client side: no finding, no response request
        assert db.scalars(select(Finding)).all() == []
        assert db.scalars(select(ResponseRequest)).all() == []


def test_run_is_audit_logged_without_document_text(ai):
    client, factory, ids, model, add, *_ = ai
    add("alerts.txt", BODY_MARK.encode())
    sign_in_auditor(client)
    client.post(url(ids, "/run"))
    with factory() as db:
        rows = db.scalars(select(AuditLog).where(AuditLog.action == "ai_analysis.run")).all()
        assert len(rows) == 1 and rows[0].firm_id == ids["firm_a"]
        assert rows[0].actor_id == ids["auditor"]
        assert rows[0].details["models"] == [DEFAULT_MODELS[0]]
        dump = json.dumps([r.details for r in db.scalars(select(AuditLog))])
        assert BODY_MARK not in dump and DRAFT_MARK not in dump


def test_missing_ai_service_config_is_a_clean_503(ai):
    client, _, ids, *_ = ai
    client.app.dependency_overrides[get_model_client] = lambda: None
    sign_in_auditor(client)
    assert client.post(url(ids, "/run")).status_code == 503


def test_second_model_is_tried_only_after_an_upstream_failure(ai):
    client, _, ids, model, add, *_ = ai
    add("alerts.txt", b"text")
    calls = []

    class Flaky(FakeModel):
        def analyze(self, req, model_id):
            calls.append(model_id)
            if len(calls) == 1:
                raise ModelRefused("upstream_error")
            return super().analyze(req, model_id)

    client.app.dependency_overrides[get_model_client] = lambda: Flaky()
    sign_in_auditor(client)
    run = client.post(url(ids, "/run")).json()["lastRun"]
    assert calls == list(DEFAULT_MODELS) and run["models"] == [DEFAULT_MODELS[1]]


def test_a_refusal_for_policy_never_falls_through_to_another_model(ai):
    client, _, ids, model, add, *_ = ai
    add("a.txt", b"text")
    refusing = FakeModel(error="model_not_free")
    client.app.dependency_overrides[get_model_client] = lambda: refusing
    sign_in_auditor(client)
    body = client.post(url(ids, "/run")).json()
    assert refusing.models == [DEFAULT_MODELS[0]]
    assert body["drafts"] == [] and body["lastRun"]["skipped"][0]["code"] == "model_not_free"


def test_model_cannot_cite_another_document_or_a_missing_page(ai):
    client, _, ids, model, add, *_ = ai
    add("a.txt", b"one page of text")

    def good(req):
        return ModelFinding(document_id=req.document_id, page=1, issue="ok")

    findings = [
        good,
        lambda req: ModelFinding(document_id="someone-elses-doc", page=1, issue="x"),
        lambda req: ModelFinding(document_id=req.document_id, page=7, issue="invented page"),
    ]
    client.app.dependency_overrides[get_model_client] = lambda: FakeModel(findings=findings)
    sign_in_auditor(client)
    drafts = client.post(url(ids, "/run")).json()["drafts"]
    assert [d["body"] for d in drafts] == ["ok"]


def test_a_run_covers_at_most_the_file_limit_and_says_so(ai):
    client, _, ids, model, add, *_ = ai
    for n in range(MAX_DOCUMENTS + 2):
        add(f"f{n}.txt", b"text")
    sign_in_auditor(client)
    run = client.post(url(ids, "/run")).json()["lastRun"]
    assert run["documentsAnalyzed"] == MAX_DOCUMENTS
    assert [s["code"] for s in run["skipped"]] == ["over_limit", "over_limit"]


# --- SAR safety -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "We filed a SAR last month.",
        "sar narrative attached",
        "S.A.R. decision log",
        "Ｓ Ａ Ｒ",
        "s​a​r",
        "Suspicious\nActivity   Report filing",
        "suspicious-activity-reports",
        "FinCEN Form 111",
    ],
)
def test_sar_text_is_blocked_before_any_model_call(ai, text):
    client, _, ids, model, add, *_ = ai
    add("notes.txt", text.encode())
    sign_in_auditor(client)
    run = client.post(url(ids, "/run")).json()["lastRun"]
    assert model.requests == []
    assert run["documentsAnalyzed"] == 0
    assert run["skipped"][0]["code"] == "sar_content"
    assert "SAR" in run["skipped"][0]["reason"]


def test_sar_inside_a_pdf_is_blocked(ai):
    client, _, ids, model, add, *_ = ai
    add("policy.pdf", pdf_bytes("Page one is fine.", "Page two: our SAR procedure."))
    sign_in_auditor(client)
    run = client.post(url(ids, "/run")).json()["lastRun"]
    assert model.requests == [] and run["skipped"][0]["code"] == "sar_content"


def test_sar_in_the_file_name_is_blocked(ai):
    client, _, ids, model, add, *_ = ai
    add("SAR-2025-q1.txt", b"ordinary text")
    sign_in_auditor(client)
    assert client.post(url(ids, "/run")).json()["lastRun"]["skipped"][0]["code"] == "sar_content"
    assert model.requests == []


def test_files_on_restricted_items_are_skipped_and_never_even_read(ai):
    client, _, ids, model, add, reads, _ = ai
    doc = add("filing.txt", b"ordinary text", item="restricted_a")
    sign_in_auditor(client)
    run = client.post(url(ids, "/run")).json()["lastRun"]
    assert model.requests == [] and doc not in reads
    assert run["skipped"][0]["code"] == "restricted_item"


def test_a_file_also_linked_to_a_restricted_item_is_restricted(ai):
    client, factory, ids, model, add, reads, _ = ai
    doc = add("shared.txt", b"ordinary text")
    with factory() as db:
        db.add(
            DocumentItemLink(
                firm_id=ids["firm_a"],
                engagement_id=ids["engagement_a"],
                item_instance_id=ids["restricted_a"],
                document_id=doc,
                linked_by_id=ids["client_a"],
            )
        )
        db.commit()
    sign_in_auditor(client)
    run = client.post(url(ids, "/run")).json()["lastRun"]
    assert model.requests == [] and doc not in reads
    assert run["skipped"][0]["code"] == "restricted_item"


def test_ordinary_files_still_reach_the_model(ai):
    client, _, ids, model, add, *_ = ai
    add("training.txt", b"Annual AML training was held on 2025-03-01. Sarah attended.")
    sign_in_auditor(client)
    assert client.post(url(ids, "/run")).json()["lastRun"]["documentsAnalyzed"] == 1
    assert len(model.requests) == 1


# --- odd files ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "content", "code"),
    [
        ("empty.txt", b"", "empty"),
        ("scan.png", b"\x89PNG\r\n\x1a\n....", "unsupported_type"),
        ("fake.pdf", b"just text, not a pdf", "unreadable"),
        ("broken.pdf", b"%PDF-1.4 truncated garbage", "unreadable"),
        ("binary.txt", b"abc\x00\x01\x02def", "unreadable"),
        ("blank.txt", b"   \n  \n", "no_text"),
        ("huge.txt", b"x" * (21 * 1024 * 1024), "too_large"),
        ("gone.txt", None, "storage_unavailable"),
    ],
)
def test_odd_files_are_skipped_cleanly_with_a_reason(ai, name, content, code):
    client, _, ids, model, add, *_ = ai
    add(name, content)
    sign_in_auditor(client)
    response = client.post(url(ids, "/run"))
    assert response.status_code == 200
    skipped = response.json()["lastRun"]["skipped"]
    assert [s["code"] for s in skipped] == [code] and skipped[0]["reason"]
    assert model.requests == []


def test_a_real_pdf_keeps_its_pages_for_citation(ai):
    client, _, ids, model, add, *_ = ai
    add("program.pdf", pdf_bytes("Alpha page text", "Bravo page text"))
    sign_in_auditor(client)
    client.post(url(ids, "/run"))
    request = model.requests[0]
    assert request.page_count == 2
    assert "[page 1]" in request.text and "Bravo page text" in request.text


# --- injection ------------------------------------------------------------------------


def test_prompt_injection_text_cannot_change_what_a_draft_is(ai):
    client, factory, ids, model, add, *_ = ai
    injected = (Path("data/synthetic") / "prompt-injection.txt").read_bytes()
    add("injection.txt", injected)
    sign_in_auditor(client)
    drafts = client.post(url(ids, "/run")).json()["drafts"]
    assert all(d["status"] == "pending" for d in drafts)
    request = model.requests[0]
    assert "Ignore all prior instructions" in request.text  # present only as document data
    assert request.firm_id == ids["firm_a"]
    with factory() as db:
        assert db.scalars(select(Finding)).all() == []


def test_model_output_with_extra_or_forged_fields_is_discarded():
    def respond(request: httpx.Request) -> httpx.Response:
        forged = {
            "findings": [
                {"document_id": "d", "page": 1, "issue": "x", "status": "approved", "sign": True}
            ]
        }
        return httpx.Response(200, json=forged)

    client = HttpAdapterClient(
        "http://ai.internal", "svc-token", httpx.Client(transport=httpx.MockTransport(respond))
    )
    req = AnalyzeRequest(
        firm_id="f", engagement_id="e", user_id="u", item_id="AML-BD-001", document_id="d",
        source="synthetic", text="t",
    )  # fmt: skip
    with pytest.raises(ModelRefused) as err:
        client.analyze(req, DEFAULT_MODELS[0])
    assert err.value.code == "bad_output"


def test_http_client_sends_the_token_and_maps_refusals_without_leaking_it():
    seen = {}

    def respond(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["authorization"]
        seen["params"] = dict(request.url.params)
        return httpx.Response(403, json={"detail": "sar_blocked"})

    client = HttpAdapterClient(
        "http://ai.internal/", "svc-token-xyz", httpx.Client(transport=httpx.MockTransport(respond))
    )
    req = AnalyzeRequest(
        firm_id="f", engagement_id="e", user_id="u", item_id="AML-BD-001", document_id="d",
        source="synthetic", text="t",
    )  # fmt: skip
    with pytest.raises(ModelRefused) as err:
        client.analyze(req, DEFAULT_MODELS[0])
    assert err.value.code == "sar_blocked" and "svc-token-xyz" not in str(err.value)
    assert seen["auth"] == "Bearer svc-token-xyz" and seen["params"]["model"] == DEFAULT_MODELS[0]


# --- accept, edit, reject -------------------------------------------------------------


def _first_draft(client, ids, kind="finding"):
    drafts = client.post(url(ids, "/run")).json()["drafts"]
    return next(d for d in drafts if d["kind"] == kind)


def test_accept_creates_only_an_internal_draft_finding_with_the_citation(ai):
    client, factory, ids, model, add, *_ = ai
    add("alerts.txt", b"text")
    sign_in_auditor(client)
    draft = _first_draft(client, ids)
    accepted = client.post(f"/auditor/ai-drafts/{draft['id']}/accept").json()
    assert accepted["status"] == "accepted" and accepted["findingId"]
    with factory() as db:
        finding = db.get(Finding, accepted["findingId"])
        assert finding.status == "draft" and finding.created_by_id == ids["auditor"]
        assert finding.citations == [{"document": "alerts.txt", "page": 1}]
        assert finding.condition == DRAFT_MARK
        assert db.scalars(select(ResponseRequest)).all() == []  # nothing released to a client
    assert client.post(f"/auditor/ai-drafts/{draft['id']}/accept").status_code == 409
    assert client.post(f"/auditor/ai-drafts/{draft['id']}/reject").status_code == 409


def test_edit_changes_the_text_and_marks_it_edited_then_accept_uses_it(ai):
    client, factory, ids, model, add, *_ = ai
    add("alerts.txt", b"text")
    sign_in_auditor(client)
    draft = _first_draft(client, ids)
    edited = client.put(
        f"/auditor/ai-drafts/{draft['id']}", json={"title": "Better title", "body": "Edited body"}
    ).json()
    assert edited["edited"] is True and edited["body"] == "Edited body"
    assert edited["status"] == "pending"
    accepted = client.post(f"/auditor/ai-drafts/{draft['id']}/accept").json()
    with factory() as db:
        finding = db.get(Finding, accepted["findingId"])
        assert finding.title == "Better title" and finding.condition == "Edited body"
    assert (
        client.put(
            f"/auditor/ai-drafts/{draft['id']}", json={"title": "t", "body": "b"}
        ).status_code
        == 409
    )


def test_reject_closes_the_draft_and_creates_nothing(ai):
    client, factory, ids, model, add, *_ = ai
    add("alerts.txt", b"text")
    sign_in_auditor(client)
    draft = _first_draft(client, ids)
    assert client.post(f"/auditor/ai-drafts/{draft['id']}/reject").json()["status"] == "rejected"
    with factory() as db:
        assert db.scalars(select(Finding)).all() == []
        actions = {r.action for r in db.scalars(select(AuditLog))}
        assert "ai_draft.rejected" in actions


def test_client_request_drafts_become_an_internal_recommendation_only(ai):
    client, factory, ids, model, add, *_ = ai
    add("alerts.txt", b"text")
    sign_in_auditor(client)
    draft = _first_draft(client, ids, "client_request")
    accepted = client.post(f"/auditor/ai-drafts/{draft['id']}/accept").json()
    with factory() as db:
        finding = db.get(Finding, accepted["findingId"])
        assert finding.title.startswith("Suggested client request:")
        assert finding.recommendation and finding.status == "draft"


def test_edit_validation_rejects_blank_text(ai):
    client, _, ids, model, add, *_ = ai
    add("alerts.txt", b"text")
    sign_in_auditor(client)
    draft = _first_draft(client, ids)
    assert (
        client.put(
            f"/auditor/ai-drafts/{draft['id']}", json={"title": " ", "body": "b"}
        ).status_code
        == 422
    )


# --- firm isolation and client blindness ----------------------------------------------


def test_unassigned_auditor_cannot_run_see_or_change_ai_work(ai):
    client, factory, ids, model, add, *_ = ai
    add("alerts.txt", b"text")
    sign_in_auditor(client)
    draft = _first_draft(client, ids)
    with factory() as db:
        db.get(Engagement, ids["engagement_a"]).auditor_id = None
        db.commit()
    assert client.get(url(ids)).status_code == 404
    assert client.post(url(ids, "/run")).status_code == 404
    for call in (
        client.put(f"/auditor/ai-drafts/{draft['id']}", json={"title": "t", "body": "b"}),
        client.post(f"/auditor/ai-drafts/{draft['id']}/accept"),
        client.post(f"/auditor/ai-drafts/{draft['id']}/reject"),
    ):
        assert call.status_code == 404
    with factory() as db:
        assert db.get(AiDraft, draft["id"]).status == "pending"


def test_unknown_and_guessed_draft_ids_are_404(ai):
    client, *_ = ai
    sign_in_auditor(client)
    assert client.post("/auditor/ai-drafts/not-a-real-id/accept").status_code == 404
    assert (
        client.post("/auditor/ai-drafts/00000000-0000-0000-0000-000000000000/reject").status_code
        == 404
    )


def test_other_firms_files_are_never_read_or_listed_in_this_run(ai):
    client, factory, ids, model, add, reads, _ = ai
    foreign = add("beta.txt", b"beta text", engagement="engagement_b", firm="firm_b", item="item_b")
    mine = add("alpha.txt", b"alpha text")
    sign_in_auditor(client)
    body = client.post(url(ids, "/run")).json()
    assert reads == [mine] and foreign not in reads
    assert {r.document_id for r in model.requests} == {mine}
    assert all(d["documentId"] == mine for d in body["drafts"])
    other = client.get(url(ids, engagement="engagement_b")).json()
    assert other["drafts"] == [] and other["lastRun"] is None  # B's view holds none of A's work


def test_a_document_row_with_the_wrong_firm_is_not_analysed(ai):
    client, factory, ids, model, add, reads, _ = ai
    stray = add("stray.txt", b"stray", engagement="engagement_a", firm="firm_b")
    sign_in_auditor(client)
    client.post(url(ids, "/run"))
    assert stray not in reads and model.requests == []


def test_client_never_sees_ai_drafts_runs_or_accepted_findings(ai):
    client, factory, ids, model, add, *_ = ai
    add("alerts.txt", b"text")
    sign_in_auditor(client)
    draft = _first_draft(client, ids)
    client.post(f"/auditor/ai-drafts/{draft['id']}/accept")
    client.post("/auth/sign-out")
    sign_in_client(client)
    spec = client.app.openapi()["paths"]
    assert not any("ai" in p.lower().split("/")[1:2] for p in spec)
    for path in (
        f"/engagements/{ids['engagement_a']}",
        f"/engagements/{ids['engagement_a']}/checklist",
        f"/engagements/{ids['engagement_a']}/response-requests",
        "/engagements/current",
        f"/engagements/{ids['engagement_a']}/feed",
    ):
        response = client.get(path)
        text = response.text
        assert DRAFT_MARK not in text and "ai_draft" not in text.lower(), path
        assert "documentsAnalyzed" not in text and "aiDraft" not in text, path
    assert client.get(url(ids)).status_code == 403
    assert client.post(f"/auditor/ai-drafts/{draft['id']}/accept").status_code == 403


# --- fixed facts ----------------------------------------------------------------------


def test_rubric_is_marked_draft_and_covers_five_core_items():
    assert "DRAFT, needs Quentin's approval" in RUBRIC_PATH.read_text()
    assert rubric_items() == {"AML-BD-009", "AML-BD-012", "AML-BD-004", "AML-BD-003", "AML-BD-021"}
    assert rubric_for("AML-BD-999") == []


def test_default_models_are_exact_free_ids_on_the_allowlist():
    allow = json.loads(Path("ai_adapter/allowlist.json").read_text())["models"]
    ids = {m["id"] for m in allow}
    assert set(DEFAULT_MODELS) == ids and len(ids) == 2
    assert all(m.endswith(":free") and ":online" not in m for m in DEFAULT_MODELS)


def test_no_secret_values_in_ai_code_or_fixtures():
    for folder in ("audit_engine", "ai_adapter"):
        for path in Path(folder).rglob("*"):
            if path.is_file() and path.suffix in {".py", ".json", ".yaml"}:
                text = path.read_text()
                assert "sk-or-" not in text, path


def test_alembic_has_one_head_including_the_ai_tables():
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    heads = ScriptDirectory.from_config(Config("alembic.ini")).get_heads()
    assert heads == ["a130_ai_analysis"]
