import io
import os
import stat

import httpx
import pytest
import respx
from pydantic import SecretStr

from app.config import Settings
from app.egnyte_client import EgnyteClient
from app.egnyte_client.cli import main
from tests.conftest import (
    ACCESS,
    BASE,
    CLIENT_ID,
    CLIENT_SECRET,
    PASSWORD,
    REFRESH,
    USERNAME,
    SleepRecorder,
    token_json,
)

SECRETS = (ACCESS, REFRESH, CLIENT_ID, CLIENT_SECRET, PASSWORD)


def settings(**kw) -> Settings:
    base = dict(
        egnyte_domain="testfirm",
        egnyte_api_key=SecretStr(CLIENT_ID),
        egnyte_client_secret=SecretStr(CLIENT_SECRET),
        egnyte_username=USERNAME,
        egnyte_password=SecretStr(PASSWORD),
        egnyte_dev_root="/Shared/AINS-Dev",
    )
    base.update(kw)
    return Settings(_env_file=None, **base)


def run(argv, s=None):
    out, err = io.StringIO(), io.StringIO()
    code = main(
        argv,
        settings=s or settings(),
        client_factory=lambda st: EgnyteClient.from_settings(
            st, sleep=SleepRecorder(), max_per_second=0
        ),
        out=out,
        err=err,
    )
    return code, out.getvalue(), err.getvalue()


def assert_no_secrets(*texts: str) -> None:
    for t in texts:
        for s in SECRETS:
            assert s not in t


@respx.mock
def test_whoami_prints_no_secrets() -> None:
    respx.post(f"{BASE}/puboauth/token").mock(return_value=httpx.Response(200, json=token_json()))
    respx.get(f"{BASE}/pubapi/v1/userinfo").mock(
        return_value=httpx.Response(
            200, json={"id": 7, "username": USERNAME, "first_name": "A", "last_name": "B"}
        )
    )
    code, out, err = run(["whoami"])
    assert code == 0
    assert f"username: {USERNAME}" in out and "domain: testfirm" in out
    assert_no_secrets(out, err)


@respx.mock
def test_ls_and_mkdir_and_upload_download(tmp_path) -> None:
    respx.post(f"{BASE}/puboauth/token").mock(return_value=httpx.Response(200, json=token_json()))
    respx.get(f"{BASE}/pubapi/v1/fs/Shared/AINS-Dev").mock(
        return_value=httpx.Response(
            200,
            json={
                "path": "/Shared/AINS-Dev",
                "folders": [{"name": "c1", "path": "/Shared/AINS-Dev/c1"}],
                "files": [{"name": "x.pdf", "path": "/Shared/AINS-Dev/x.pdf", "size": 1234}],
            },
        )
    )
    respx.post(f"{BASE}/pubapi/v1/fs/Shared/AINS-Dev/c2").mock(
        return_value=httpx.Response(201, json={"path": "/Shared/AINS-Dev/c2", "folder_id": "f"})
    )
    respx.post(f"{BASE}/pubapi/v1/fs-content/Shared/AINS-Dev/c2/a.txt").mock(
        return_value=httpx.Response(200, json={})
    )
    respx.get(f"{BASE}/pubapi/v1/fs-content/Shared/AINS-Dev/c2/a.txt").mock(
        return_value=httpx.Response(200, content=b"data")
    )
    s = settings(egnyte_access_token=SecretStr(ACCESS))

    code, out, err = run(["ls", "/Shared/AINS-Dev"], s)
    assert code == 0 and "[dir]  c1/" in out and "x.pdf  (1,234 bytes)" in out

    code, out, _ = run(["mkdir", "/Shared/AINS-Dev/c2"], s)
    assert code == 0 and "Folder ready: /Shared/AINS-Dev/c2" in out

    local = tmp_path / "a.txt"
    local.write_bytes(b"data")
    code, out, _ = run(["upload", str(local), "/Shared/AINS-Dev/c2/a.txt"], s)
    assert code == 0 and "Uploaded" in out

    dest = tmp_path / "out"
    dest.mkdir()
    code, out, err = run(["download", "/Shared/AINS-Dev/c2/a.txt", str(dest)], s)
    assert code == 0 and (dest / "a.txt").read_bytes() == b"data"
    assert_no_secrets(out, err)


def test_cli_path_guard_error() -> None:
    code, out, err = run(["ls", "/Shared/Clients"], settings(egnyte_access_token=SecretStr(ACCESS)))
    assert code == 1 and "outside allowed root" in err and out == ""


@respx.mock
def test_cli_auth_error_no_secrets() -> None:
    respx.post(f"{BASE}/puboauth/token").mock(
        return_value=httpx.Response(403, json={"message": f"bad {PASSWORD}"})
    )
    code, out, err = run(["whoami"])
    assert code == 1 and "error:" in err
    assert_no_secrets(out, err)


@respx.mock
def test_get_token_writes_file_only(tmp_path) -> None:
    respx.post(f"{BASE}/puboauth/token").mock(return_value=httpx.Response(200, json=token_json()))
    dest = tmp_path / "egnyte-token.env"
    code, out, err = run(["get-token", str(dest)])
    assert code == 0
    assert_no_secrets(out, err)
    assert "not printed" in out
    content = dest.read_text()
    assert f"EGNYTE_ACCESS_TOKEN={ACCESS}" in content
    assert f"EGNYTE_REFRESH_TOKEN={REFRESH}" in content
    assert stat.S_IMODE(os.stat(dest).st_mode) == 0o600


def test_get_token_refuses_overwrite(tmp_path) -> None:
    dest = tmp_path / "t.env"
    dest.write_text("keep")
    code, _, err = run(["get-token", str(dest)])
    assert code == 1 and "--force" in err and dest.read_text() == "keep"


@pytest.mark.parametrize("cmd", [["whoami"], ["ls", "/Shared/AINS-Dev"]])
def test_missing_domain(cmd) -> None:
    code, _, err = run(cmd, settings(egnyte_domain=""))
    assert code == 1 and "EGNYTE_DOMAIN" in err
