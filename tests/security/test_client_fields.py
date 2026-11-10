"""S-09: each client read contract needs a proof and cannot serialize finding fields."""

import json

from tests.security.test_tenant_isolation import _send
from tests.test_backend_api import sign_in_auditor, sign_in_client
from tests.test_responses_requested import release
from tests.test_route_isolation import INVENTORY, LEAKS, _seed_internal_material, fill

READS = {
    ("GET", "/engagements/current"),
    ("GET", "/engagements/{engagement_id}/questionnaire"),
    ("GET", "/engagements/{engagement_id}/responses-requested"),
}
MUTATIONS = {
    ("POST", "/engagements/{engagement_id}/documents"),
    ("POST", "/engagements/{engagement_id}/items/{item_id}/documents"),
    ("POST", "/engagements/{engagement_id}/items/{item_id}/na"),
    ("POST", "/engagements/{engagement_id}/items/{item_id}/representations"),
    ("POST", "/engagements/{engagement_id}/questionnaire/answers"),
    ("POST", "/engagements/{engagement_id}/questionnaire/items/{item_id}/na-review"),
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
    assert {(m, p) for m, p, kind in INVENTORY if kind == "client"} == READS | MUTATIONS


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


def test_client_mutation_responses_never_serialize_finding_fields(backend):
    client, factory, original, *_ = backend
    _seed_internal_material(factory, original)
    ids = {**original, "engagement_id": original["engagement_a"], "item_id": original["item_a"]}
    sign_in_client(client)
    for method, path in sorted(MUTATIONS):
        response = _send(client, method, path, ids)
        # Some existing declaration/review paths intentionally refuse a client action.
        assert response.status_code in {200, 201, 403, 409}, (method, path, response.status_code)
        check_fields(response.json())
        assert not any(marker in response.text for marker in LEAKS)
