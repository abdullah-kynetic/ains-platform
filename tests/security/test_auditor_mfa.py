"""S-04: MFA is required on every auditor request; hashed recovery codes are single-use."""

from sqlalchemy import select

from app.auth.router import _new_recovery_codes
from app.auth.security import hash_mfa_recovery_code
from app.database.models import MFARecoveryCode, User
from tests.test_backend_api import AUDITOR_PASSWORD, sign_in_auditor
from tests.test_route_isolation import INVENTORY, fill


def test_existing_auditor_session_without_mfa_cannot_access_any_auditor_route(backend):
    client, factory, ids, *_ = backend
    sign_in_auditor(client)
    with factory() as db:
        db.get(User, ids["auditor"]).mfa_enabled = False
        db.commit()
    for method, path, kind in INVENTORY:
        if kind == "auditor":
            response = client.request(method, fill(path, ids))
            assert response.status_code == 403, (method, path, response.status_code)
            assert response.json()["detail"] == "Auditor MFA enrollment is required"
    # Ending an authenticated session remains possible after MFA is disabled.
    assert client.post("/auth/sign-out").status_code == 204


def test_recovery_codes_are_hashed_and_consumed_once(backend):
    client, factory, ids, *_ = backend
    with factory() as db:
        codes = _new_recovery_codes(db, db.get(User, ids["auditor"]))
        db.commit()
        records = db.scalars(select(MFARecoveryCode)).all()
        assert {row.code_hash for row in records} == {hash_mfa_recovery_code(c) for c in codes}
        assert not set(codes) & {row.code_hash for row in records}
    payload = {"email": "auditor@example.test", "password": AUDITOR_PASSWORD, "mfa_code": codes[0]}
    assert client.post("/auth/password", json=payload).status_code == 200
    client.cookies.clear()
    denied = client.post("/auth/password", json=payload)
    assert denied.status_code == 401 and "set-cookie" not in denied.headers
    with factory() as db:
        used = db.scalar(
            select(MFARecoveryCode).where(
                MFARecoveryCode.code_hash == hash_mfa_recovery_code(codes[0])
            )
        )
        assert used.used_at is not None
