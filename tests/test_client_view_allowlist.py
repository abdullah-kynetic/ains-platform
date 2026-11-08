"""Client-facing payloads expose only an allowlist of fields; internal material never appears.

Adding a field to a client response must be a deliberate change to these sets.
"""

import json

from app.database.models import CheckResult, Document
from tests.test_backend_api import backend, sign_in_client  # noqa: F401
from tests.test_route_isolation import LEAKS, _seed_internal_material  # noqa: F401

TOP = {
    "collectionProgress", "dueDate", "engagementType", "firmName", "id", "reviewPeriod",
    "sections", "unassignedDocuments",
}  # fmt: skip
SECTION = {"id", "items", "title"}
ITEM = {
    "allowedEvidenceTypes", "canUpload", "description", "files", "followUp", "id",
    "naMarkedByRole", "naReviewState", "reason", "representation", "requestId", "restricted",
    "status", "title",
}  # fmt: skip
FILE = {"id", "name", "size", "sha256", "uploadedAt", "feedback"}
CHECK_MARKER = "CHECK-DETAIL-MARKER-9d1"


def test_client_engagement_payload_has_only_allowlisted_fields(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    _seed_internal_material(factory, ids)
    with factory() as db:
        doc = Document(
            firm_id=ids["firm_a"],
            engagement_id=ids["engagement_a"],
            item_instance_id=ids["item_a"],
            uploaded_by_id=ids["client_a"],
            original_name="synthetic.txt",
            size_bytes=3,
            egnyte_path="/synthetic",
            sha256="a" * 64,
            version="1",
        )
        db.add(doc)
        db.flush()
        db.add(
            CheckResult(
                firm_id=ids["firm_a"],
                document_id=doc.id,
                check_type="synthetic",
                status="failed",
                details={"note": CHECK_MARKER},
                citations=[{"page": 1, "text": CHECK_MARKER}],
            )
        )
        db.commit()
    sign_in_client(client)
    body = client.get("/engagements/current").json()
    assert set(body) == TOP
    for section in body["sections"]:
        assert set(section) == SECTION
        for item in section["items"]:
            assert set(item) == ITEM
            for file in item["files"]:
                assert set(file) == FILE
    text = json.dumps(body)
    for marker in (*LEAKS, CHECK_MARKER):
        assert marker not in text


def test_questionnaire_payload_has_only_allowlisted_fields(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    _seed_internal_material(factory, ids)
    sign_in_client(client)
    body = client.get(f"/engagements/{ids['engagement_a']}/questionnaire").json()
    assert set(body) == {"engagementId", "questions"}
    for question in body["questions"]:
        assert not set(question) & {"internalNotes", "assessment", "findings", "notes"}
    assert not any(marker in json.dumps(body) for marker in LEAKS)
