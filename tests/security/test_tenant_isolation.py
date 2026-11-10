"""S-08: fail on unregistered routes and deny real foreign/unassigned resource IDs."""

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select

from app.auth.dependencies import get_authenticated_user, get_current_user
from app.auth.security import new_invitation_token
from app.database.models import AuditorTask, ClientInvitation, Engagement, EngagementReport
from tests.test_auditor_assignment import _invoice_body, _real_finding
from tests.test_backend_api import sign_in_auditor, sign_in_client
from tests.test_route_isolation import (
    BODY_OVERRIDES,
    INVENTORY,
    LEAKS,
    _example,
    _seed_internal_material,
)
from tests.test_workflow_routes import real_workflow_rows

CASES = [
    line.split()
    for line in Path("tests/security/tenant_denial_cases.txt").read_text().splitlines()
    if line and not line.startswith("#")
]


def _has_identity_dependency(node):
    return node.call in {get_current_user, get_authenticated_user} or any(
        _has_identity_dependency(child) for child in node.dependencies
    )


def test_every_protected_route_has_registered_denial_and_shared_identity_checks(backend):
    client = backend[0]
    expected = {(m, p) for m, p, kind in INVENTORY if kind != "public"}
    registered = {(m, p) for m, p, _case in CASES}
    assert registered == expected, f"Add real scope-denial proof: {expected - registered}"
    assert len(registered) == len(CASES)
    by_route = {(method, path): case for method, path, case in CASES}
    for method, path, kind in INVENTORY:
        if kind == "public":
            continue
        case = (
            "session_claims"
            if kind == "session"
            else "new_workspace"
            if path == "/auditor/workspaces"
            else "client_scope"
            if kind == "client"
            else "auditor_scope"
        )
        assert by_route[method, path] == case
    assert all(
        case in {"client_scope", "auditor_scope", "new_workspace", "session_claims"}
        for _, _, case in CASES
    )
    for route in client.app.routes:
        if hasattr(route, "dependant") and any((m, route.path) in expected for m in route.methods):
            assert _has_identity_dependency(route.dependant), route.path


def _send(client, method, path, ids):
    spec = client.app.openapi()
    operation = spec["paths"][path][method.lower()]
    aliases = {"firmId": "firm_id", "engagementId": "engagement_id", "itemId": "item_id"}

    def bind(value):
        if isinstance(value, dict):
            return {key: ids.get(aliases.get(key, key), bind(v)) for key, v in value.items()}
        if isinstance(value, list):
            return [bind(v) for v in value]
        return value

    kwargs = {
        "params": {
            p["name"]: ids.get(aliases.get(p["name"], p["name"]), _example(p["schema"], spec))
            for p in operation.get("parameters", [])
            if p["in"] == "query" and p.get("required")
        }
    }
    body = operation.get("requestBody", {}).get("content", {}).get("application/json")
    if body:
        kwargs["json"] = bind(BODY_OVERRIDES.get((method, path)) or _example(body["schema"], spec))
    if method == "POST" and path.endswith("/documents"):
        kwargs["files"] = {"file": ("synthetic.txt", b"synthetic", "text/plain")}
    target = re.sub(r"\{(\w+)\}", lambda match: ids[match[1]], path)
    return client.request(method, target, **kwargs)


def test_foreign_client_scope_is_denied_on_every_registered_client_route(backend):
    client, _factory, original, *_ = backend
    ids = {
        **original,
        "firm_id": original["firm_a"],
        "engagement_id": original["engagement_a"],
        "item_id": original["item_a"],
    }
    ids.update(real_workflow_rows(_factory, original))
    sign_in_client(client, "beta-client@example.test")
    for method, path, case in CASES:
        if case != "client_scope":
            continue
        response = _send(client, method, path, ids)
        if path == "/engagements/current":
            assert response.status_code == 200 and response.json()["id"] == original["engagement_b"]
            assert original["engagement_a"] not in response.text
        else:
            assert response.status_code in {403, 404}, (method, path, response.status_code)


def test_revoked_assignment_denies_real_resources_and_filters_collections(backend):
    client, factory, original, *_ = backend
    ids = {
        **original,
        "firm_id": original["firm_a"],
        "engagement_id": original["engagement_a"],
        "item_id": original["item_a"],
    }
    _seed_internal_material(factory, original)
    ids["finding_id"] = _real_finding(factory, original)
    ids.update(real_workflow_rows(factory, original))
    sign_in_auditor(client)
    invoice = client.post("/auditor/invoices", json=_invoice_body(original))
    assert invoice.status_code == 201
    ids["invoice_id"] = invoice.json()["id"]
    _, digest = new_invitation_token()
    with factory() as db:
        invitation = ClientInvitation(
            firm_id=ids["firm_id"],
            engagement_id=ids["engagement_id"],
            email="synthetic-proof-invite@example.test",
            name="Synthetic",
            token_hash=digest,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            created_by_id=ids["auditor"],
        )
        db.add(invitation)
        db.flush()
        ids["invitation_id"] = invitation.id
        ids["report_id"] = db.scalar(select(EngagementReport.id))
        ids["task_id"] = db.scalar(select(AuditorTask.id))
        for engagement in db.scalars(select(Engagement)):
            engagement.auditor_id = None
        db.commit()
    for method, path, case in CASES:
        if case != "auditor_scope":
            continue
        response = _send(client, method, path, ids)
        scoped = "{" in path or path.startswith("/auditor/audit-log") or method != "GET"
        assert response.status_code == (404 if scoped else 200), (
            method,
            path,
            response.status_code,
        )
        assert not any(marker in response.text for marker in LEAKS)
        if not scoped:
            # No metadata-only shell (firm names, contacts, IDs, counts) may survive.
            assert response.json() == [], path
    client.cookies.clear()
    sign_in_client(client, "beta-client@example.test")
    assert _send(client, "POST", "/auditor/workspaces", ids).status_code == 403
