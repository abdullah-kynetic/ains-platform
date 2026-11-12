"""The AI service overlay: shape, least privilege and outbound limits. Static checks only."""

import re
import subprocess
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
OVERLAY = ROOT / "deploy" / "docker-compose.ai.yml"
compose = yaml.safe_load(OVERLAY.read_text())
service = compose["services"]["ai-adapter"]


def test_overlay_only_adds_the_ai_service():
    assert list(compose["services"]) == ["ai-adapter"]  # no existing service is redefined


def test_service_is_locked_down_and_not_published():
    assert "ports" not in service  # reachable only from the private network
    assert service["expose"] == ["8100"]
    assert service["read_only"] is True
    assert service["cap_drop"] == ["ALL"]
    assert "no-new-privileges:true" in service["security_opt"]
    assert service["mem_limit"] == "300m"
    assert service["command"][:2] == ["uvicorn", "ai_adapter.main:app"]
    assert "--workers" not in service["command"]  # counters live in one process


def test_service_gets_only_the_ai_env_file_and_no_secret_values():
    assert service["env_file"] == "/etc/kien/ai.env"
    text = OVERLAY.read_text()
    for env in service["environment"].values():
        assert "sk-" not in env and "@" not in env  # no key, no credentialed URL
    assert not re.search(r"(?i)(api[_-]?key|token|password)\s*[:=]\s*[^\s#$]+", text)


def test_only_ai_service_joins_the_egress_network():
    assert "ai_egress" in service["networks"] and "backend" in service["networks"]
    assert "services" not in compose["networks"]["ai_egress"]
    assert compose["networks"]["ai_egress"]["ipam"]["config"][0]["subnet"] == "172.31.40.0/24"
    assert not compose["networks"]["ai_egress"].get("internal")  # it is the one way out


def test_overlay_does_not_touch_the_servers_deploy_files():
    base = yaml.safe_load((ROOT / "deploy" / "docker-compose.prod.yml").read_text())
    assert "ai-adapter" not in base["services"]  # the overlay is a separate, additive file


def test_env_example_lists_names_only():
    text = (ROOT / "deploy" / "ai" / "ai.env.example").read_text()
    for name in (
        "AI_ENABLED",
        "AI_SERVICE_TOKEN",
        "OPENROUTER_API_KEY",
        "AI_ANALYSIS_ENABLED",
        "AI_SERVICE_URL",
        "AI_OWNERSHIP_DATABASE_URL",
    ):
        assert name in text
    assert "AI_ENABLED=false" in text
    for line in text.splitlines():
        if "=" in line and not line.startswith("#"):
            assert line.split("=", 1)[1].split("#")[0].strip() in ("", "false")


def test_readonly_role_reads_ids_only():
    sql = (ROOT / "deploy" / "ai" / "readonly-role.sql").read_text()
    grants = re.findall(r"GRANT SELECT[^;]*;", sql)
    assert grants and all("(" in g for g in grants)  # column-level only
    assert not re.search(r"(?i)INSERT|UPDATE|DELETE|PASSWORD '", sql)


def test_egress_script_allows_only_openrouter_https_and_dns():
    script = ROOT / "deploy" / "ai" / "egress-firewall.sh"
    text = script.read_text()
    assert 'HOST="openrouter.ai"' in text and "--dport 443" in text and "-j DROP" in text
    assert subprocess.run(["bash", "-n", str(script)]).returncode == 0


def test_dockerfile_gives_the_service_a_writable_state_directory():
    text = (ROOT / "Dockerfile").read_text()
    assert "/var/lib/kien-ai" in text and "chown ains:ains /var/lib/kien-ai" in text


def test_asgi_entrypoint_is_fail_closed_by_default(monkeypatch):
    for name in ("AI_ENABLED", "AI_SERVICE_TOKEN", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    from ai_adapter.main import app

    client = TestClient(app)
    assert client.get("/health").json() == {"status": "ok"}
    body = {"firm_id": "f", "engagement_id": "e", "user_id": "u"}
    assert client.post("/v1/analyze?model=x", json=body).status_code == 401
    blank = {"Authorization": "Bearer "}  # an empty token must never match an unset one
    assert client.post("/v1/analyze?model=x", json=body, headers=blank).status_code == 401
