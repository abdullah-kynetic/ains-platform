"""Route inventory, role gates, cross-tenant denial and client-visibility checks (synthetic data).

Role gates here are server-side checks; UI role gates are not authorization.
"""

import re
from pathlib import Path

import pytest

from app.database.models import (
    AuditorTask,
    ChecklistItemInstance,
    Engagement,
    EngagementReport,
    FindingDraft,
    TaskPriority,
)
from tests.test_backend_api import backend, sign_in_auditor, sign_in_client  # noqa: F401

INVENTORY = [
    line.split()
    for line in Path("tests/route_inventory.txt").read_text().splitlines()
    if line and not line.startswith("#")
]
FINDING = "FINDING-MARKER-7c1"
TASK = "TASK-MARKER-7c2"
NOTE = "INTERNAL-NOTE-MARKER-7c3"
REPORT = "DRAFT-REPORT-MARKER-7c4"
# Routes whose schema demands a particular value that the generic example cannot guess.
BODY_OVERRIDES = {("PATCH", "/auditor/tasks/{task_id}"): {"title": "Synthetic task"}}
BODY_VALIDATED_FIRST: set[tuple[str, str]] = set()
LEAKS = (FINDING, TASK, NOTE, REPORT)


def fill(path: str, ids: dict[str, str]) -> str:
    values = {
        "engagement_id": ids["engagement_a"],
        "item_id": ids["item_a"],
        "firm_id": ids["firm_a"],
    }
    return re.sub(r"\{(\w+)\}", lambda m: values.get(m.group(1), "unknown-id"), path)


def _example(schema: dict, spec: dict, name: str = ""):
    """Smallest value that satisfies a JSON schema, enough to get past request validation."""
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        return _example(spec["components"]["schemas"][name], spec, name)
    for key in ("anyOf", "oneOf"):
        if key in schema:
            options = [o for o in schema[key] if o.get("type") != "null"]
            return _example(options[0], spec)
    if "enum" in schema:
        return schema["enum"][0]
    kind = schema.get("type")
    if kind == "object":
        props = schema.get("properties", {})
        return {k: _example(props[k], spec, k) for k in schema.get("required", [])}
    if kind == "array":
        n = schema.get("minItems", 0)
        return [_example(schema["items"], spec)] * n
    if kind == "integer" or kind == "number":
        return max(schema.get("minimum", 1), 1)
    if kind == "boolean":
        return True
    fmt = schema.get("format")
    if "[a-f0-9]{64}" in schema.get("pattern", ""):
        return "a" * 64
    if "@" in schema.get("pattern", "") or "email" in name.lower():
        return "synthetic@example.test"
    if fmt == "date":
        return "2025-01-01"
    if fmt == "date-time":
        return "2025-01-01T00:00:00Z"
    if fmt == "email":
        return "synthetic@example.test"
    return "x" * max(schema.get("minLength", 1), 1)


def request_with_valid_shape(client, method: str, path: str, ids: dict[str, str]):
    """Send a request that passes validation, so any denial comes from the access checks."""
    spec = client.app.openapi()
    op = next(
        o
        for p, ms in spec["paths"].items()
        for m, o in ms.items()
        if (m.upper(), p) == (method, path)
    )
    params = {
        p["name"]: _example(p["schema"], spec)
        for p in op.get("parameters", [])
        if p["in"] == "query" and p.get("required")
    }
    body = op.get("requestBody", {}).get("content", {}).get("application/json")
    kwargs = {"params": params}
    if body:
        kwargs["json"] = BODY_OVERRIDES.get((method, path)) or _example(body["schema"], spec)
    return client.request(method, fill(path, ids), **kwargs)


def test_inventory_matches_the_running_application(backend):  # noqa: F811
    client = backend[0]
    actual = {(m.upper(), p) for p, ms in client.app.openapi()["paths"].items() for m in ms}
    listed = {(method, path) for method, path, _ in INVENTORY}
    assert actual == listed, (
        "Routes changed: update tests/route_inventory.txt and add isolation tests. "
        f"new={sorted(actual - listed)} removed={sorted(listed - actual)}"
    )
    for _method, path, kind in INVENTORY:
        expected = (
            "auditor"
            if path.startswith("/auditor")
            else "client"
            if path.startswith("/engagements")
            else None
        )
        assert kind == expected or (expected is None and kind in {"public", "session"}), path
    assert {p for m, p, k in INVENTORY if k == "public"} <= {
        "/health",
        "/auth/capabilities",
        "/auth/password",
        "/auth/magic-link",
        "/auth/magic-link/verify",
        "/auth/password-reset/request",
        "/auth/password-reset/confirm",
        "/auth/invitations/{token}",
        "/auth/invitations/accept",
        "/auth/auditor/mfa/enrollment",
        "/auth/auditor/mfa/enrollment/confirm",
    }


def test_every_non_public_route_requires_a_session(backend):  # noqa: F811
    client, _, ids, *_ = backend
    for method, path, kind in INVENTORY:
        if kind == "public":
            continue
        response = client.request(method, fill(path, ids))
        assert response.status_code == 401, (method, path, response.status_code)


def test_client_role_is_denied_on_every_auditor_route(backend):  # noqa: F811
    client, _, ids, *_ = backend
    sign_in_client(client)
    for method, path, kind in INVENTORY:
        if kind != "auditor":
            continue
        response = client.request(method, fill(path, ids))
        if response.status_code == 422:
            response = request_with_valid_shape(client, method, path, ids)
        if response.status_code == 422:
            # Body validation runs before the in-handler role check, so an empty body cannot
            # reach it. Such routes are listed explicitly; a new one must be added on purpose.
            assert (method, path) in BODY_VALIDATED_FIRST, (method, path)
            continue
        assert response.status_code == 403, (method, path, response.status_code)


def test_auditor_cannot_use_client_routes(backend):  # noqa: F811
    client, _, ids, *_ = backend
    sign_in_auditor(client)
    for method, path, kind in INVENTORY:
        if kind != "client":
            continue
        response = client.request(method, fill(path, ids))
        if method == "GET":
            continue  # an assigned auditor may view the client-safe engagement views
        assert response.status_code in {403, 404, 405, 422}, (method, path, response.status_code)


def test_client_of_another_firm_is_denied_on_client_routes(backend):  # noqa: F811
    client, _, ids, *_ = backend
    sign_in_client(client, "beta-client@example.test")  # firm B
    for method, path, kind in INVENTORY:
        if kind != "client" or (method, path) == ("GET", "/engagements/current"):
            continue
        if path.endswith("/documents"):
            response = client.post(
                fill(path, ids), files={"file": ("synthetic.txt", b"synthetic", "text/plain")}
            )
        else:
            response = request_with_valid_shape(client, method, path, ids)
        assert response.status_code in {403, 404}, (method, path, response.status_code)


def test_unassigned_auditor_gets_not_found_on_engagement_scoped_reads(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    with factory() as db:
        db.get(Engagement, ids["engagement_a"]).auditor_id = None
        db.commit()
    sign_in_auditor(client)
    eng = ids["engagement_a"]
    for path in (
        f"/auditor/engagements/{eng}/workspace",
        f"/auditor/engagements/{eng}/summary",
        f"/auditor/engagements/{eng}/invitations",
    ):
        assert client.get(path).status_code == 404, path
    assert eng not in {e["id"] for e in client.get("/auditor/engagements").json()}


def _seed_internal_material(factory, ids):
    with factory() as db:
        db.add(
            FindingDraft(
                firm_id=ids["firm_a"],
                engagement_id=ids["engagement_a"],
                title=FINDING,
                body=FINDING,
                severity="high",
            )
        )
        db.add(
            AuditorTask(
                firm_id=ids["firm_a"],
                engagement_id=ids["engagement_a"],
                assignee_id=ids["auditor"],
                title=TASK,
                priority=TaskPriority.HIGH,
            )
        )
        db.add(
            EngagementReport(
                firm_id=ids["firm_a"],
                engagement_id=ids["engagement_a"],
                created_by_id=ids["auditor"],
                content={"summary": REPORT},
                snapshot={},
            )
        )
        item = db.get(ChecklistItemInstance, ids["item_a"])
        item.internal_notes = NOTE
        item.assessment = "supported"
        db.commit()


def test_client_never_sees_findings_notes_tasks_or_unreleased_reports(backend):  # noqa: F811
    client, factory, ids, *_ = backend
    _seed_internal_material(factory, ids)
    sign_in_client(client)
    eng = ids["engagement_a"]
    bodies = []
    for path in (
        "/engagements/current",
        f"/engagements/{eng}/questionnaire",
        "/auth/session",
        "/auth/capabilities",
    ):
        response = client.get(path)
        assert response.status_code == 200, path
        bodies.append(response.text)
    # Auditor surfaces refuse the client, and the refusal itself reveals nothing.
    for method, path, kind in INVENTORY:
        if kind == "auditor":
            bodies.append(client.request(method, fill(path, ids)).text)
    joined = "\n".join(bodies).casefold()
    for marker in LEAKS:
        assert marker.casefold() not in joined
    assert '"findings"' not in joined and "internal_notes" not in joined
    assert "assessment" not in joined


def test_missing_and_foreign_resources_are_indistinguishable_to_a_client(backend):  # noqa: F811
    client, _, ids, *_ = backend
    sign_in_client(client)
    foreign = client.get(f"/engagements/{ids['engagement_b']}/questionnaire")
    missing = client.get("/engagements/does-not-exist/questionnaire")
    assert foreign.status_code == missing.status_code == 404
    assert foreign.json() == missing.json()


def test_restricted_item_rejects_uploads_for_the_owning_client(backend):  # noqa: F811
    client, _, ids, fake_ingestor, _ = backend
    sign_in_client(client)
    response = client.post(
        f"/engagements/{ids['engagement_a']}/items/{ids['restricted_a']}/documents",
        files={"file": ("synthetic.txt", b"synthetic", "text/plain")},
    )
    assert response.status_code == 403
    assert fake_ingestor.calls == 0


@pytest.mark.parametrize("path", ["/auth/session", "/auth/onboarding"])
def test_session_routes_work_for_a_signed_in_user(backend, path):  # noqa: F811
    client, *_ = backend
    sign_in_client(client)
    assert client.get(path).status_code == 200
