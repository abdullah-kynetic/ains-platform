"""Static checks on the production deploy files, and the proxy-header behaviour they rely on."""

import subprocess
from pathlib import Path

import yaml
from starlette.testclient import TestClient
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

COMPOSE = yaml.safe_load(Path("deploy/docker-compose.prod.yml").read_text())
SERVICES = COMPOSE["services"]


def test_only_caddy_publishes_ports():
    published = [name for name, svc in SERVICES.items() if svc.get("ports")]
    assert published == ["caddy"]
    assert SERVICES["caddy"]["ports"] == ["80:80", "443:443"]


def test_postgres_is_on_internal_network_only():
    assert SERVICES["postgres"]["networks"] == ["backend"]
    assert COMPOSE["networks"]["backend"]["internal"] is True


def test_migrations_run_once_in_a_dedicated_service():
    assert SERVICES["migrate"]["command"] == ["alembic", "upgrade", "head"]
    assert SERVICES["migrate"]["restart"] == "no"
    for name in ("api", "worker"):
        assert SERVICES[name]["environment"]["RUN_MIGRATIONS"] == "0"
        assert (
            SERVICES[name]["depends_on"]["migrate"]["condition"] == "service_completed_successfully"
        )


def test_entrypoint_skips_migrations_only_when_disabled():
    script = Path("scripts/docker-entrypoint.sh").read_text()
    for flag, expect_migrate in (("0", False), ("1", True), (None, True)):
        env = {"PATH": "/usr/bin:/bin"}
        if flag is not None:
            env["RUN_MIGRATIONS"] = flag
        stub = f"alembic() {{ echo MIGRATED; }}; {script.replace('set -eu', 'set -eu', 1)}"
        out = subprocess.run(
            ["sh", "-c", stub, "entry", "echo", "started"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        assert ("MIGRATED" in out) is expect_migrate
        assert "started" in out


def test_api_trusts_forwarded_headers_only_from_pinned_caddy_address():
    command = SERVICES["api"]["command"]
    assert "--proxy-headers" in command
    caddy_ip = SERVICES["caddy"]["networks"]["edge"]["ipv4_address"]
    assert f"--forwarded-allow-ips={caddy_ip}" in command
    assert "--no-proxy-headers" not in command
    subnet = COMPOSE["networks"]["edge"]["ipam"]["config"][0]["subnet"]
    assert caddy_ip.rsplit(".", 1)[0] == subnet.rsplit(".", 1)[0]
    assert SERVICES["api"]["read_only"] is True
    assert SERVICES["api"]["cap_drop"] == ["ALL"]


def _app_with_proxy_trust(trusted: str) -> TestClient:
    async def echo(scope, receive, send):
        body = scope["client"][0].encode()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": body})

    wrapped = ProxyHeadersMiddleware(echo, trusted_hosts=trusted)
    return TestClient(wrapped, client=("172.30.0.2", 5000))


def test_forwarded_client_ip_is_used_from_proxy_and_ignored_from_others():
    headers = {"X-Forwarded-For": "203.0.113.9"}
    assert _app_with_proxy_trust("172.30.0.2").get("/", headers=headers).text == "203.0.113.9"
    # A request that does not come from the trusted proxy cannot spoof its address.
    spoofing = _app_with_proxy_trust("172.30.0.99")
    assert spoofing.get("/", headers=headers).text == "172.30.0.2"


def test_prod_image_does_not_download_aws_ca_bundle():
    assert "rds.amazonaws.com" not in Path("Dockerfile").read_text()
