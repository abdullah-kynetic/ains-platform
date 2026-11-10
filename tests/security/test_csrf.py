"""S-03: every inventoried unsafe route rejects a foreign Origin before handlers run."""

from sqlalchemy import func, select

from app.database.models import AuditLog
from tests.test_route_isolation import INVENTORY, fill


def test_every_state_changing_route_rejects_foreign_origin(backend):
    client, factory, ids, ingestor, *_ = backend
    with factory() as db:
        before = db.scalar(select(func.count()).select_from(AuditLog))
    checked = set()
    for method, path, _kind in INVENTORY:
        if method not in {"POST", "PUT", "PATCH", "DELETE"}:
            continue
        response = client.request(
            method,
            fill(path, ids),
            headers={
                "Origin": "https://foreign.example.test",
            },
        )
        assert response.status_code == 403, (method, path, response.status_code)
        assert response.json() == {"detail": "Cross-site request refused"}
        assert "set-cookie" not in response.headers
        checked.add((method, path))
    assert checked and len(checked) == sum(
        method in {"POST", "PUT", "PATCH", "DELETE"} for method, *_ in INVENTORY
    )
    assert ingestor.calls == 0
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(AuditLog)) == before
