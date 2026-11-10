"""L2-6e: the assembled report draft, section edits and Word/PDF downloads. Auditor-only."""

import io

from alembic import command
from alembic.config import Config
from docx import Document as DocxDocument
from sqlalchemy import create_engine, inspect, select

from app.database.models import (
    AuditLog,
    Base,
    EngagementReport,
    Finding,
    SampleItem,
    SampleSet,
)
from tests.test_backend_api import backend, sign_in_auditor, sign_in_client  # noqa: F401


def _draft(ids):
    return f"/auditor/engagements/{ids['engagement_a']}/report-draft"


def _finding(factory, ids, status="approved", title="Alert closures", response="") -> str:
    with factory() as db:
        finding = Finding(
            firm_id=ids["firm_a"],
            engagement_id=ids["engagement_a"],
            title=title,
            rule="Rule text",
            condition="Condition text",
            cause="Cause text",
            effect="Effect text",
            recommendation="Recommendation text",
            severity="high",
            citations=[{"document": "x.pdf", "page": 1}],
            status=status,
            management_response=response,
            created_by_id=ids["auditor"],
        )
        db.add(finding)
        db.commit()
        return finding.id


def _by_id(client, ids):
    return {s["id"]: s for s in client.get(_draft(ids)).json()["sections"]}


def test_draft_is_assembled_from_stored_entries_and_excludes_draft_findings(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    sign_in_auditor(client)
    body = client.get(_draft(ids)).json()
    assert set(body) == {"engagementId", "sections", "generatedAt"}
    assert [s["id"] for s in body["sections"]] == ["scope", "approach", "results", "limitations"]
    assert all(set(s) == {"id", "title", "body"} for s in body["sections"])
    scope = body["sections"][0]["body"]
    assert "Synthetic Alpha Securities" in scope and "January 1, 2025 to December 31, 2025" in scope
    assert "The audit firm performed" in scope
    first = client.get(f"/auditor/engagements/{ids['engagement_a']}/checklist-tests").json()[0]
    client.patch(
        f"/auditor/engagements/{ids['engagement_a']}/checklist-tests/{first['requestId']}",
        json={"conclusion": "partial"},
    )
    _finding(factory, ids, status="draft", title="Hidden draft")
    fid = _finding(factory, ids, status="responded", title="Alert closures", response="We agree.")
    _finding(factory, ids, status="issued", title="Second", response="")
    with factory() as db:
        db.add(
            SampleSet(
                firm_id=ids["firm_a"],
                engagement_id=ids["engagement_a"],
                area="a",
                population=3,
                sample_size=1,
                method="m",
                created_by_id=ids["auditor"],
                items=[
                    SampleItem(
                        firm_id=ids["firm_a"], position=0, reference="ITEM-001", result="exception"
                    )
                ],
            )
        )
        db.commit()
    sections = _by_id(client, ids)
    assert (
        "Partial: 1." in sections["results"]["body"]
        and "Not yet concluded:" in sections["results"]["body"]
    )
    assert "1 populations with 1 exception noted." in sections["approach"]["body"]
    assert f"finding-{fid}" in sections
    titles = [s["title"] for s in client.get(_draft(ids)).json()["sections"]]
    assert titles[3:5] == ["Finding 1: Alert closures", "Finding 2: Second"]
    assert "Hidden draft" not in str(sections)
    assert "Management response: We agree." in sections[f"finding-{fid}"]["body"]
    assert "Management response: Not yet received." in str(sections)
    assert titles[-1] == "Limitations"


def test_section_edit_replaces_text_and_is_audited(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    sign_in_auditor(client)
    fid = _finding(factory, ids)
    url = f"{_draft(ids)}/sections"
    saved = client.put(f"{url}/scope", json={"body": "Our own scope text."})
    assert saved.status_code == 200 and saved.json() == {
        "id": "scope",
        "title": "Scope and objective",
        "body": "Our own scope text.",
    }
    assert _by_id(client, ids)["scope"]["body"] == "Our own scope text."
    assert client.put(f"{url}/finding-{fid}", json={"body": "Edited finding."}).status_code == 200
    client.put(f"{url}/scope", json={"body": "Second edit."})
    assert _by_id(client, ids)["scope"]["body"] == "Second edit."
    assert client.put(f"{url}/nope", json={"body": "x"}).status_code == 404
    assert client.put(f"{url}/finding-nope", json={"body": "x"}).status_code == 404
    assert client.put(f"{url}/scope", json={"body": "x" * 20001}).status_code == 422
    assert client.put(f"{url}/scope", json={"body": "x", "extra": 1}).status_code == 422
    with factory() as db:
        logs = list(
            db.scalars(select(AuditLog).where(AuditLog.action == "report_draft.section_edited"))
        )
        assert len(logs) == 3 and all(
            "text_length" in log.details and "body" not in log.details for log in logs
        )
        assert {log.firm_id for log in logs} == {ids["firm_a"]}
        # A final report locks the draft until it is reopened.
        db.add(
            EngagementReport(
                firm_id=ids["firm_a"],
                engagement_id=ids["engagement_a"],
                created_by_id=ids["auditor"],
                status="final",
                content={},
                snapshot={},
            )
        )
        db.commit()
    assert client.put(f"{url}/scope", json={"body": "late"}).status_code == 409
    assert _by_id(client, ids)["scope"]["body"] == "Second edit."


def test_word_and_pdf_downloads_render_the_draft_and_escape_text(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    sign_in_auditor(client)
    _finding(factory, ids, title="Wires <b>& more</b>")
    client.put(f"{_draft(ids)}/sections/scope", json={"body": "Line one\nLine two & <tag>"})
    word = client.get(f"{_draft(ids)}/docx")
    assert word.status_code == 200 and "wordprocessingml" in word.headers["content-type"]
    assert word.headers["content-disposition"].startswith('attachment; filename="report-draft-')
    assert word.headers["cache-control"] == "no-store"
    text = "\n".join(p.text for p in DocxDocument(io.BytesIO(word.content)).paragraphs)
    assert "Draft. Not signed." in text and "Line two & <tag>" in text
    assert "Finding 1: Wires <b>& more</b>" in text
    pdf = client.get(f"{_draft(ids)}/pdf")
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")
    with factory() as db:
        formats = [
            log.details["format"]
            for log in db.scalars(
                select(AuditLog).where(AuditLog.action == "report_draft.downloaded")
            )
        ]
    assert formats == ["docx", "pdf"]


def test_only_the_assigned_auditor_can_use_the_draft(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    sign_in_client(client)
    for method, path in (
        ("GET", ""),
        ("PUT", "/sections/scope"),
        ("GET", "/docx"),
        ("GET", "/pdf"),
    ):
        kw = {"json": {"body": "x"}} if method == "PUT" else {}
        assert client.request(method, _draft(ids) + path, **kw).status_code == 403, path
    client.cookies.clear()
    sign_in_auditor(client)
    from app.database.models import Engagement

    with factory() as db:
        db.get(Engagement, ids["engagement_a"]).auditor_id = None
        db.commit()
    for method, path in (
        ("GET", ""),
        ("PUT", "/sections/scope"),
        ("GET", "/docx"),
        ("GET", "/pdf"),
    ):
        kw = {"json": {"body": "x"}} if method == "PUT" else {}
        assert client.request(method, _draft(ids) + path, **kw).status_code == 404, path


def test_draft_sections_are_not_in_any_client_view(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    sign_in_auditor(client)
    _finding(factory, ids, title="CLIENT-MUST-NOT-SEE")
    client.put(f"{_draft(ids)}/sections/scope", json={"body": "AUDITOR-DRAFT-TEXT"})
    client.cookies.clear()
    sign_in_client(client)
    for path in (
        "/engagements/current",
        f"/engagements/{ids['engagement_a']}/progress",
        f"/engagements/{ids['engagement_a']}/report",
        f"/engagements/{ids['engagement_a']}/responses-requested",
    ):
        text = client.get(path).text
        assert "CLIENT-MUST-NOT-SEE" not in text and "AUDITOR-DRAFT-TEXT" not in text, path


def test_report_section_edit_migration_up_down_and_idempotent():
    config = Config("alembic.ini")
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.stamp(config, "a125_report_section_edits")
        command.downgrade(config, "a124_findings_responses")
        assert "report_section_edits" not in set(inspect(connection).get_table_names())
        command.upgrade(config, "a125_report_section_edits")
        assert "report_section_edits" in set(inspect(connection).get_table_names())
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.stamp(config, "a124_findings_responses")
        command.upgrade(config, "a125_report_section_edits")
    engine.dispose()
