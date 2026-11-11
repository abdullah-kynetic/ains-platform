"""Two auditing practices, two client firms: neither side can read or change the other's data.

Practice One (auditor@example.test) audits Synthetic Alpha only. Practice Two (a second auditor)
audits Synthetic Beta only. Each side gets a document, a flag with a thread, a finding with a
released response request, a workpaper, a sample set, a task, a report, an invoice and audit-log
rows, all tagged with a side-specific marker. Every auditor route and every client route is then
called with the other side's real ids, and every list route is read; the other side's markers
must never appear and nothing on the other side may change. Synthetic data only.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, date, datetime

import pyotp
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.auth.security import hash_password
from app.database.models import (
    AuditLog,
    AuditorTask,
    Document,
    DocumentIssue,
    Engagement,
    EngagementReport,
    Finding,
    Invoice,
    InvoiceIssuer,
    InvoiceLineItem,
    IssueMessage,
    Practice,
    ResponseRequest,
    SampleItem,
    SampleSet,
    User,
    UserRole,
    Workpaper,
)
from tests.test_backend_api import (  # noqa: F401
    AUDITOR_PASSWORD,
    MFA_SECRET,
    backend,
    sign_in_client,
)
from tests.test_route_isolation import BODY_OVERRIDES, INVENTORY, _example

SECOND_AUDITOR = "practice-two-auditor@example.test"
MARK = {"a": "PRACTICE-ONE-ALPHA-9d1", "b": "PRACTICE-TWO-BETA-9d2"}
# The only path id here is a catalog request id (shared by every practice); the route writes the
# caller's own practice rubric, so success is expected and the leak check still applies.
OWN_SCOPED = {("PUT", "/auditor/firm/rubric/{request_id}")}
# Tables whose row count for a firm must not change while the other side probes it.
WATCHED = (
    Document,
    DocumentIssue,
    IssueMessage,
    Finding,
    ResponseRequest,
    Workpaper,
    SampleSet,
    AuditorTask,
    EngagementReport,
    Invoice,
)


def _seed_side(db, side: str, firm_id: str, engagement_id: str, item_id: str, auditor_id: str):
    mark = MARK[side]
    client_id = db.scalar(
        select(User.id).where(User.firm_id == firm_id, User.role == UserRole.CLIENT)
    )
    doc = Document(
        firm_id=firm_id,
        engagement_id=engagement_id,
        item_instance_id=item_id,
        uploaded_by_id=client_id,
        original_name=f"{mark}-policy.pdf",
        content_type="application/pdf",
        size_bytes=10,
        egnyte_path=f"/Shared/AINS-Dev/{firm_id}/{engagement_id}/{mark}.pdf",
        sha256=("a" if side == "a" else "b") * 64,
        number="1.1",
    )
    db.add(doc)
    db.flush()
    issue = DocumentIssue(
        firm_id=firm_id,
        engagement_id=engagement_id,
        item_instance_id=item_id,
        document_id=doc.id,
        kind="outdated",
        created_by_id=auditor_id,
    )
    db.add(issue)
    db.flush()
    db.add(
        IssueMessage(
            firm_id=firm_id,
            issue_id=issue.id,
            author_id=auditor_id,
            author_role="auditor",
            body=f"{mark} flag thread",
        )
    )
    finding = Finding(
        firm_id=firm_id,
        engagement_id=engagement_id,
        title=f"{mark} finding",
        condition=f"{mark} condition",
        status="issued",
        citations=[{"documentId": doc.id, "page": 1}],
        created_by_id=auditor_id,
    )
    db.add(finding)
    db.flush()
    request = ResponseRequest(
        firm_id=firm_id,
        engagement_id=engagement_id,
        finding_id=finding.id,
        title=f"{mark} response request",
        request_text=f"{mark} please respond",
        released_by_id=auditor_id,
    )
    workpaper = Workpaper(
        firm_id=firm_id,
        engagement_id=engagement_id,
        request_id="AML-BD-004",
        procedure=f"{mark} procedure",
        preparer_id=auditor_id,
    )
    sample = SampleSet(
        firm_id=firm_id,
        engagement_id=engagement_id,
        area=f"{mark} sample area",
        population=10,
        sample_size=1,
        method="Synthetic",
        created_by_id=auditor_id,
    )
    task = AuditorTask(
        firm_id=firm_id,
        engagement_id=engagement_id,
        assignee_id=auditor_id,
        title=f"{mark} task",
    )
    report = EngagementReport(
        firm_id=firm_id,
        engagement_id=engagement_id,
        created_by_id=auditor_id,
        content={"summary": f"{mark} report"},
        snapshot={},
    )
    db.add_all([request, workpaper, sample, task, report])
    db.flush()
    sample_item = SampleItem(firm_id=firm_id, set_id=sample.id, position=0, reference=mark)
    issuer = InvoiceIssuer(id=f"issuer-{side}", auditor_id=auditor_id, next_number=2)
    db.add_all([sample_item, issuer])
    db.flush()
    invoice = Invoice(
        issuer_id=issuer.id,
        firm_id=firm_id,
        engagement_id=engagement_id,
        auditor_id=auditor_id,
        number=1,
        status="sent",
        issue_date=date(2026, 1, 1),
        due_date=date(2026, 2, 1),
        notes=f"{mark} invoice note",
        subtotal_cents=1000,
        total_cents=1000,
    )
    invoice.line_items = [
        InvoiceLineItem(
            description=f"{mark} line",
            quantity=1,
            rate_cents=1000,
            amount_cents=1000,
            position=0,
        )
    ]
    db.add(invoice)
    db.flush()
    db.add(
        AuditLog(
            firm_id=firm_id,
            actor_id=auditor_id,
            action="synthetic.isolation_marker",
            entity_type="engagement",
            entity_id=engagement_id,
            details={"marker": mark},
        )
    )
    return {
        "engagement_id": engagement_id,
        "item_id": item_id,
        "firm_id": firm_id,
        "document_id": doc.id,
        "issue_id": issue.id,
        "finding_record_id": finding.id,
        "finding_id": finding.id,
        "response_request_id": request.id,
        "request_id": "AML-BD-004",
        "set_id": sample.id,
        "sample_item_id": sample_item.id,
        "task_id": task.id,
        "report_id": report.id,
        "invoice_id": invoice.id,
        "member_id": auditor_id,
        "section_id": "summary",
    }


def _setup(factory, ids):
    with factory() as db:
        one, two = Practice(name=f"{MARK['a']} practice"), Practice(name=f"{MARK['b']} practice")
        db.add_all([one, two])
        db.flush()
        first = db.get(User, ids["auditor"])
        first.practice_id, first.team_role = one.id, "partner"
        second = User(
            email=SECOND_AUDITOR,
            name=f"{MARK['b']} auditor",
            role=UserRole.AUDITOR,
            password_hash=hash_password(AUDITOR_PASSWORD),
            mfa_secret=MFA_SECRET,
            mfa_enabled=True,
            accepted_at=datetime.now(UTC),
            practice_id=two.id,
            team_role="partner",
        )
        db.add(second)
        db.flush()
        db.get(Engagement, ids["engagement_b"]).auditor_id = second.id
        sides = {
            "a": _seed_side(db, "a", ids["firm_a"], ids["engagement_a"], ids["item_a"], first.id),
            "b": _seed_side(db, "b", ids["firm_b"], ids["engagement_b"], ids["item_b"], second.id),
        }
        db.commit()
    return sides


def _sign_in_auditor(client: TestClient, email: str) -> None:
    client.post("/auth/sign-out")
    client.cookies.clear()
    response = client.post(
        "/auth/password",
        json={
            "email": email,
            "password": AUDITOR_PASSWORD,
            "mfa_code": pyotp.TOTP(MFA_SECRET).now(),
        },
    )
    assert response.status_code == 200, response.text


def _fill(path: str, values: dict[str, str]) -> str:
    return re.sub(r"\{(\w+)\}", lambda m: values.get(m.group(1), "unknown-id"), path)


def _counts(factory, firm_id: str) -> dict[str, int]:
    with factory() as db:
        return {
            model.__name__: db.scalar(
                select(func.count()).select_from(model).where(model.firm_id == firm_id)
            )
            for model in WATCHED
        }


def _shaped(client, method: str, path: str, values: dict[str, str]):
    """Send a request that passes validation, every path id taken from ``values``."""
    spec = client.app.openapi()
    op = spec["paths"][path][method.lower()]
    params = {
        p["name"]: _example(p["schema"], spec)
        for p in op.get("parameters", [])
        if p["in"] == "query" and p.get("required")
    }
    if "firm_id" in params:
        params["firm_id"] = values["firm_id"]
    body = op.get("requestBody", {}).get("content", {}).get("application/json")
    kwargs: dict = {"params": params}
    if body:
        kwargs["json"] = BODY_OVERRIDES.get((method, path)) or _example(body["schema"], spec)
    return client.request(method, _fill(path, values), **kwargs)


def _probe_auditor_routes(client, factory, sides, own: str, other: str) -> list[str]:
    """Call every auditor route with the other side's real ids; return any leak or success."""
    problems = []
    foreign = sides[other]
    before = _counts(factory, foreign["firm_id"])
    for method, path, kind in INVENTORY:
        if kind != "auditor":
            continue
        if path == "/auditor/search":
            response = client.get(path, params={"q": MARK[other]})
        else:
            response = _shaped(client, method, path, foreign)
        if MARK[other] in response.text:
            problems.append(f"LEAK {method} {path} -> {response.status_code}")
        if "{" in path and response.status_code < 300 and (method, path) not in OWN_SCOPED:
            problems.append(f"ALLOWED {method} {path} -> {response.status_code}")
    if _counts(factory, foreign["firm_id"]) != before:
        problems.append(f"{own} changed {other}'s rows")
    return problems


def test_each_practice_is_sealed_from_the_other_on_every_auditor_route(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    sides = _setup(factory, ids)
    _sign_in_auditor(client, "auditor@example.test")
    problems = _probe_auditor_routes(client, factory, sides, "a", "b")
    _sign_in_auditor(client, SECOND_AUDITOR)
    problems += _probe_auditor_routes(client, factory, sides, "b", "a")
    assert problems == []


def test_each_client_is_sealed_from_the_other_on_every_client_route(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    sides = _setup(factory, ids)
    for own, other, email in (
        ("a", "b", "alpha-client@example.test"),
        ("b", "a", "beta-client@example.test"),
    ):
        client.post("/auth/sign-out")
        client.cookies.clear()
        sign_in_client(client, email)
        foreign = sides[other]
        before = _counts(factory, foreign["firm_id"])
        for method, path, kind in INVENTORY:
            if kind != "client" or (method, path) == ("GET", "/engagements/current"):
                continue
            if path.endswith("/documents"):
                response = client.post(
                    _fill(path, foreign),
                    files={"file": ("synthetic.txt", b"synthetic", "text/plain")},
                )
            elif method == "GET":
                response = client.get(_fill(path, foreign))
            else:
                response = _shaped(client, method, path, foreign)
            assert response.status_code in {403, 404}, (own, method, path, response.status_code)
            assert MARK[other] not in response.text, (own, method, path)
        assert _counts(factory, foreign["firm_id"]) == before
        current = client.get("/engagements/current")
        assert MARK[other] not in current.text


def test_lists_feeds_search_and_audit_log_show_only_own_practice(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    sides = _setup(factory, ids)
    for own, other, email in (
        ("a", "b", "auditor@example.test"),
        ("b", "a", SECOND_AUDITOR),
    ):
        _sign_in_auditor(client, email)
        mine, theirs = sides[own], sides[other]
        seen = []
        for method, path, kind in INVENTORY:
            if kind != "auditor" or method != "GET" or "{" in path:
                continue
            params = {"q": "synthetic"} if path == "/auditor/search" else {}
            if path.startswith("/auditor/audit-log"):
                params = {"firm_id": mine["firm_id"]}
            response = client.get(path, params=params)
            seen.append(path)
            assert MARK[other] not in response.text, (own, path)
            for key in ("engagement_id", "document_id", "issue_id", "report_id", "invoice_id"):
                assert theirs[key] not in response.text, (own, path, key)
        assert "/auditor/audit-log" in seen and "/auditor/clients" in seen
        # Own audit chain is readable, verifies, and holds only own-firm rows.
        log = client.get("/auditor/audit-log", params={"firm_id": mine["firm_id"]})
        assert log.status_code == 200
        assert {row["firm_id"] for row in log.json()["items"]} == {mine["firm_id"]}
        chain = client.get("/auditor/audit-log/verify-chain", params={"firm_id": mine["firm_id"]})
        assert chain.status_code == 200 and chain.json()["valid"] is True
        # The other firm's chain is refused outright.
        for route in ("/auditor/audit-log", "/auditor/audit-log/verify-chain"):
            denied = client.get(route, params={"firm_id": theirs["firm_id"]})
            assert denied.status_code in {403, 404}, (own, route)
            assert MARK[other] not in denied.text
        # The practice team list names only own members.
        team = client.get("/auditor/firm/team")
        assert team.status_code == 200
        assert MARK[other] not in json.dumps(team.json())
