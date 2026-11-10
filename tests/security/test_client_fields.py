"""S-09: each client read contract needs a proof and cannot serialize finding fields."""

import json

import pytest

from app.database.models import ChecklistItemInstance
from tests.security.test_tenant_isolation import _send
from tests.test_backend_api import sign_in_auditor, sign_in_client
from tests.test_responses_requested import release
from tests.test_route_isolation import INVENTORY, LEAKS, _seed_internal_material, fill
from tests.test_workflow_routes import real_workflow_rows

READS = {
    ("GET", "/engagements/current"),
    ("GET", "/engagements/{engagement_id}/questionnaire"),
    ("GET", "/engagements/{engagement_id}/responses-requested"),
    ("GET", "/engagements/{engagement_id}/progress"),
    ("GET", "/engagements/{engagement_id}/issues"),
    ("GET", "/engagements/{engagement_id}/response-requests"),
}
MUTATIONS = {
    ("POST", "/engagements/{engagement_id}/documents"): 201,
    ("POST", "/engagements/{engagement_id}/items/{item_id}/documents"): 201,
    ("POST", "/engagements/{engagement_id}/items/{item_id}/na"): 409,
    ("POST", "/engagements/{engagement_id}/items/{item_id}/na-request"): 200,
    ("POST", "/engagements/{engagement_id}/items/{item_id}/submit"): 409,
    ("POST", "/engagements/{engagement_id}/submit"): 409,
    ("POST", "/engagements/{engagement_id}/items/{item_id}/documents/{document_id}/link"): 200,
    ("DELETE", "/engagements/{engagement_id}/items/{item_id}/documents/{document_id}/link"): 404,
    ("POST", "/engagements/{engagement_id}/issues/{issue_id}/replies"): 201,
    ("POST", "/engagements/{engagement_id}/response-requests/{response_request_id}/response"): 200,
    # No finalized report exists in this fixture; tests/test_workflow_routes.py covers the view.
    ("GET", "/engagements/{engagement_id}/report"): 404,
    ("POST", "/engagements/{engagement_id}/report/confirm"): 404,
    # Object storage is not configured in this fixture; tests/security/test_downloads.py covers it.
    ("GET", "/engagements/{engagement_id}/documents/{document_id}/download"): 501,
    ("POST", "/engagements/{engagement_id}/items/{item_id}/representations"): 200,
    ("POST", "/engagements/{engagement_id}/questionnaire/answers"): 200,
    ("POST", "/engagements/{engagement_id}/questionnaire/items/{item_id}/na-review"): 403,
}
FORBIDDEN = {
    "findings",
    "severity",
    "condition",
    "cause",
    "effect",
    "recommendation",
    "citations",
    "internalNotes",
    "internal_notes",
    "assessment",
    "findingId",
}


def test_every_client_read_contract_is_registered_for_field_review():
    assert {(m, p) for m, p, kind in INVENTORY if kind == "client"} == READS | set(MUTATIONS)


def check_fields(value):
    if isinstance(value, dict):
        assert not set(value) & FORBIDDEN
        for child in value.values():
            check_fields(child)
    elif isinstance(value, list):
        for child in value:
            check_fields(child)


def test_no_client_read_serializes_finding_fields_or_unreleased_material(backend):
    client, factory, ids, *_ = backend
    _seed_internal_material(factory, ids)
    sign_in_auditor(client)
    assert release(client, ids).status_code == 200
    client.cookies.clear()
    sign_in_client(client)

    for method, path in READS:
        response = client.request(method, fill(path, ids))
        assert response.status_code == 200
        check_fields(response.json())
        assert not any(marker in json.dumps(response.json()) for marker in LEAKS)


@pytest.mark.parametrize(
    "method,path,expected", [(m, p, status) for (m, p), status in MUTATIONS.items()]
)
def test_client_mutation_responses_never_serialize_finding_fields(backend, method, path, expected):
    client, factory, original, *_ = backend
    _seed_internal_material(factory, original)
    with factory() as db:
        # A real unrestricted conditional request makes the declaration endpoint succeed.
        db.get(ChecklistItemInstance, original["item_a"]).item_key = "AML-BD-012"
        db.commit()
    ids = {**original, "engagement_id": original["engagement_a"], "item_id": original["item_a"]}
    ids.update(real_workflow_rows(factory, original))
    sign_in_client(client)
    response = _send(client, method, path, ids)
    assert response.status_code == expected, (method, path, response.status_code)
    check_fields(response.json())
    assert not any(marker in response.text for marker in LEAKS)
