"""Another auditor, using REAL finding and invoice ids, must be denied on every id-scoped route.

Unlike the route sweep (which uses placeholder ids), these ids exist, so a 404 can only come from
the assignment filter. Mutation proof: removing `Engagement.auditor_id == user.id` in
review_finding, or `visible()` scoping for invoices, makes these tests fail.
"""

from datetime import UTC, date, datetime, timedelta

from app.auth.security import hash_password
from app.database.models import (
    ChecklistItemInstance,
    Document,
    FindingDraft,
    User,
    UserRole,
)
from tests.test_backend_api import (  # noqa: F401
    AUDITOR_PASSWORD,
    backend,
    sign_in_auditor,
)


def _second_auditor(factory) -> None:
    with factory() as db:
        db.add(
            User(
                email="auditor-two@example.test",
                name="Synthetic Auditor Two",
                role=UserRole.AUDITOR,
                password_hash=hash_password(AUDITOR_PASSWORD),
                accepted_at=datetime.now(UTC),
            )
        )
        db.commit()


def _sign_in_second(client) -> None:
    client.cookies.clear()
    response = client.post(
        "/auth/password",
        json={
            "email": "auditor-two@example.test",
            "password": AUDITOR_PASSWORD,
        },
    )
    assert response.status_code == 200


def _real_finding(factory, ids) -> str:
    with factory() as db:
        doc = Document(
            firm_id=ids["firm_a"],
            engagement_id=ids["engagement_a"],
            item_instance_id=ids["item_a"],
            uploaded_by_id=ids["client_a"],
            original_name="synthetic.txt",
            size_bytes=3,
            egnyte_path="/synthetic",
            sha256="c" * 64,
            version="1",
        )
        db.add(doc)
        db.flush()
        finding = FindingDraft(
            firm_id=ids["firm_a"],
            engagement_id=ids["engagement_a"],
            document_id=doc.id,
            title="Synthetic finding",
            body="Synthetic body",
            severity="low",
            citations=[{"document_id": doc.id, "page": 1}],
        )
        db.add(finding)
        db.commit()
        assert db.get(ChecklistItemInstance, ids["item_a"]).engagement_id == ids["engagement_a"]
        return finding.id


def _invoice_body(ids) -> dict:
    today = datetime.now(UTC).date()
    return {
        "firmId": ids["firm_a"],
        "engagementId": ids["engagement_a"],
        "issueDate": str(today - timedelta(days=1)),
        "dueDate": str(today + timedelta(days=29)),
        "lineItems": [{"description": "Synthetic review", "quantity": "1", "rateCents": 1000}],
    }


def test_finding_review_is_limited_to_the_assigned_auditor(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    _second_auditor(factory)
    finding_id = _real_finding(factory, ids)
    path = f"/auditor/findings/{finding_id}"
    _sign_in_second(client)
    for body in (
        {"action": "accept"},
        {"action": "edit", "title": "Hijacked"},
        {"action": "reject"},
    ):
        assert client.patch(path, json=body).status_code == 404
    with factory() as db:
        finding = db.get(FindingDraft, finding_id)
        assert finding.title == "Synthetic finding" and finding.review_state.value == "pending"
    client.cookies.clear()
    sign_in_auditor(client)
    assert client.patch(path, json={"action": "accept"}).status_code == 200


def test_invoice_routes_are_limited_to_the_assigned_auditor(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    _second_auditor(factory)
    sign_in_auditor(client)
    created = client.post("/auditor/invoices", json=_invoice_body(ids))
    assert created.status_code == 201, created.text
    invoice_id = created.json()["id"]
    base = f"/auditor/invoices/{invoice_id}"
    _sign_in_second(client)
    assert client.get(base).status_code == 404
    assert client.patch(base, json=_invoice_body(ids)).status_code == 404
    for action in ("sent", "paid", "void"):
        body = {"amountCents": 1000, "paidDate": str(date.today())} if action == "paid" else {}
        assert client.post(f"{base}/{action}", json=body).status_code == 404, action
    assert invoice_id not in {i["id"] for i in client.get("/auditor/invoices").json()}
    client.cookies.clear()
    sign_in_auditor(client)
    assert client.get(base).status_code == 200
