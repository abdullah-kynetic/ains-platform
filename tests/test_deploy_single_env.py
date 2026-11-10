"""Single-environment deploy code (L1-3): memory budget, env isolation, Caddy, scripts."""

import re
import subprocess
from pathlib import Path

import pytest
import yaml

DEPLOY = Path("deploy")
COMPOSE = yaml.safe_load((DEPLOY / "docker-compose.prod.yml").read_text())
SERVICES = COMPOSE["services"]
LONG_RUNNING = ["postgres", "clamav", "api", "worker", "caddy", "ai-adapter"]
SECRET_NAMES = (
    "AWS_SECRET_ACCESS_KEY",
    "AWS_ACCESS_KEY_ID",
    "RESEND_API_KEY",
    "SESSION_SECRET",
    "OPENROUTER_API_KEY",
    "R2_SECRET_ACCESS_KEY",
)


def _mb(value: str) -> int:
    m = re.fullmatch(r"(\d+)([mg])", value.lower())
    assert m, value
    return int(m.group(1)) * (1024 if m.group(2) == "g" else 1)


def test_no_staging_host_anywhere():
    for path in [
        DEPLOY / "Caddyfile",
        DEPLOY / "docker-compose.prod.yml",
        *DEPLOY.glob("env-examples/*"),
    ]:
        assert "STAGING_HOST" not in path.read_text(), path
    assert not (DEPLOY / ".env.example").exists()


def test_long_running_memory_fits_the_vps():
    for name in LONG_RUNNING + ["migrate"]:
        assert "mem_limit" in SERVICES[name], name
    total = sum(_mb(SERVICES[name]["mem_limit"]) for name in LONG_RUNNING)
    assert total <= 3300, total  # 3.7 GiB host; leave room for the OS and Docker
    assert _mb(SERVICES["migrate"]["mem_limit"]) <= 400


def test_clamav_does_not_double_load_signatures():
    assert SERVICES["clamav"]["environment"]["CLAMD_CONF_ConcurrentDatabaseReload"] == "no"


def test_only_caddy_publishes_and_ai_adapter_is_private_and_off():
    assert [n for n, s in SERVICES.items() if s.get("ports")] == ["caddy"]
    ai = SERVICES["ai-adapter"]
    assert not ai.get("ports")
    assert ai["profiles"] == ["ai"]
    assert ai["environment"]["AI_ENABLED"] == "false"
    assert ai["env_file"] == "/etc/kien/ai.env"
    assert ai["read_only"] is True and ai["cap_drop"] == ["ALL"]
    assert any(v.endswith(":/var/lib/kien-ai") for v in ai["volumes"])


def test_each_service_gets_only_its_own_env_file():
    expected = {
        "postgres": "/etc/kien/postgres.env",
        "migrate": "/etc/kien/migrate.env",
        "api": "/etc/kien/app.env",
        "worker": "/etc/kien/app.env",
        "ai-adapter": "/etc/kien/ai.env",
    }
    for name, svc in SERVICES.items():
        assert svc.get("env_file") == expected.get(name), name
    # ClamAV and Caddy never see storage, email, session or AI secrets.
    for name in ("clamav", "caddy", "postgres"):
        env = SERVICES[name].get("environment", {})
        assert not any(k in env for k in SECRET_NAMES), name
    assert set(SERVICES["caddy"]["environment"]) == {"API_HOST"}


def test_env_examples_hold_names_only_and_split_secrets():
    files = {p.name: p.read_text() for p in (DEPLOY / "env-examples").glob("*.example")}
    assert set(files) >= {
        "compose.env.example",
        "postgres.env.example",
        "migrate.env.example",
        "app.env.example",
        "ai.env.example",
    }
    for name, text in files.items():
        for line in text.splitlines():
            if line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key in SECRET_NAMES or key.endswith("PASSWORD"):
                assert value == "", f"{name}: {key} must be empty"
    for name in ("compose.env.example", "postgres.env.example", "migrate.env.example"):
        assert not any(s in files[name] for s in SECRET_NAMES), name
    assert "kien_app" in files["app.env.example"]
    assert "kien_migrator" in files["migrate.env.example"]
    assert "STAGING_HOST" not in files["compose.env.example"]
    names = {
        line.split("=")[0]
        for line in (DEPLOY / "ai.env.example").read_text().splitlines()
        if "=" in line and not line.startswith("#")
    }
    assert names == {
        "AI_ENABLED",
        "OPENROUTER_API_KEY",
        "AI_SERVICE_TOKEN",
        "AI_STATE_DATABASE_URL",
    }


def test_caddy_serves_api_host_with_security_headers():
    caddy = (DEPLOY / "Caddyfile").read_text()
    assert "{$API_HOST} {" in caddy
    assert "Content-Security-Policy \"default-src 'none'; frame-ancestors 'none'\"" in caddy
    assert "Permissions-Policy" in caddy
    assert "Strict-Transport-Security" in caddy


def test_dockerfile_copies_ai_adapter_but_not_audit_engine():
    dockerfile = Path("Dockerfile").read_text()
    assert "COPY --chown=ains:ains ai_adapter ./ai_adapter" in dockerfile
    assert "audit_engine" not in dockerfile


def test_postgres_tuned_and_db_roles_least_privilege():
    cmd = SERVICES["postgres"]["command"]
    assert "shared_buffers=256MB" in cmd and "max_connections=30" in cmd
    sql = (DEPLOY / "bootstrap" / "db-roles.sql").read_text()
    for role in ("kien_migrator", "kien_app", "kien_backup"):
        assert role in sql
    assert "REVOKE CREATE ON SCHEMA public FROM PUBLIC" in sql
    assert "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO kien_app" in sql
    assert not re.search(r"PASSWORD\s+'[^:]", sql)  # passwords come only from the environment


@pytest.mark.parametrize("ip", ["40.160.150.91"])
def test_harden_refuses_the_old_shared_server(tmp_path, ip):
    result = subprocess.run(
        ["bash", "deploy/bootstrap/harden.sh"],
        env={"PATH": "/usr/bin:/bin", "KIEN_PUBLIC_IP": ip},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 3
    assert "refusing" in result.stderr


def test_deploy_scripts_exist_and_parse():
    for script in (
        "deploy.sh",
        "rollback.sh",
        "build-on-host.sh",
        "bootstrap/harden.sh",
        "bootstrap/install-timers.sh",
        "bootstrap/db-roles.sh",
    ):
        path = DEPLOY / script
        assert path.exists(), script
        subprocess.run(["bash", "-n", str(path)], check=True)


def test_build_on_host_rejects_bad_sha():
    result = subprocess.run(
        ["bash", "deploy/build-on-host.sh", "not-a-sha;rm"], capture_output=True, text=True
    )
    assert result.returncode == 2


def test_caddy_pinned_address_is_outside_the_dynamic_range():
    import ipaddress

    cfg = COMPOSE["networks"]["edge"]["ipam"]["config"][0]
    caddy_ip = ipaddress.ip_address(SERVICES["caddy"]["networks"]["edge"]["ipv4_address"])
    assert caddy_ip in ipaddress.ip_network(cfg["subnet"])
    assert caddy_ip not in ipaddress.ip_network(cfg["ip_range"])


def test_deploy_script_has_no_trailing_and_lists_that_abort_under_set_e():
    # `[ cond ] && cmd` as a statement exits the script under `set -e` when cond is false.
    for script in ("deploy/deploy.sh", "deploy/rollback.sh"):
        for line in Path(script).read_text().splitlines():
            stripped = line.strip()
            assert not re.match(r"^\[ .* \] && ", stripped), f"{script}: {stripped}"
