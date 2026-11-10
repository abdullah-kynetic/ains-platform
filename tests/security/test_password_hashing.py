"""S-01: Argon2id storage, failed verification, and login-time parameter upgrades."""

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.auth.security import hash_password, verify_and_rehash_password, verify_password
from app.database.models import User
from tests.test_backend_api import CLIENT_PASSWORD, sign_in_client


def test_hash_is_argon2id_salted_and_verifies():
    first, second = hash_password(CLIENT_PASSWORD), hash_password(CLIENT_PASSWORD)
    assert first.startswith("$argon2id$") and second.startswith("$argon2id$")
    assert first != second and CLIENT_PASSWORD not in first
    assert verify_password(CLIENT_PASSWORD, first)
    assert not verify_password("incorrect-synthetic-password", first)
    assert verify_and_rehash_password(CLIENT_PASSWORD, first) == (True, None)


def test_login_upgrades_old_parameters_without_storing_plaintext(backend):
    client, factory, ids, *_ = backend
    legacy = PasswordHash((Argon2Hasher(time_cost=1, memory_cost=1024, parallelism=1),))
    previous = legacy.hash(CLIENT_PASSWORD)
    with factory() as db:
        db.get(User, ids["client_a"]).password_hash = previous
        db.commit()
    sign_in_client(client)
    with factory() as db:
        stored = db.get(User, ids["client_a"]).password_hash
        assert stored != previous and stored.startswith("$argon2id$")
        assert CLIENT_PASSWORD not in stored and verify_password(CLIENT_PASSWORD, stored)
        assert verify_and_rehash_password(CLIENT_PASSWORD, stored) == (True, None)
