"""The real browser fixture must seed the firm served by its localhost portal."""

import os
import subprocess
import sys
from pathlib import Path


def test_live_fixture_seeds_the_browser_portal_firm(tmp_path):
    root = Path.cwd()
    code = """
import runpy
import sys
from pathlib import Path
from urllib.parse import urlsplit

fixture = runpy.run_path(sys.argv[1])
fixture["configure"](Path(sys.argv[2]))
fixture["seed"]()

from sqlalchemy import select
from app.database.models import Document, Engagement, Firm, User, UserRole
from app.database.session import get_session_factory

with get_session_factory()() as db:
    firm = db.scalar(select(Firm).where(Firm.slug == "kynetic"))
    assert firm.slug == "kynetic"
    assert urlsplit(fixture["ORIGIN"]).hostname == f"{firm.slug}.localhost"
    clients = db.scalars(select(User).where(User.role == UserRole.CLIENT)).all()
    other = db.get(Engagement, "synthetic-other-engagement")
    assert other is not None and other.firm_id != firm.id
    document = db.scalar(select(Document))
    assert document.firm_id == firm.id and document.item_instance_id
    assert document.original_name == "synthetic-review-policy.pdf"
    assert len(clients) == 2
    assert all(client.firm_id == firm.id for client in clients)
"""
    # Separate process/cwd avoids cached app settings and any repository dotenv file.
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
            str(root / "scripts/e2e_backend.py"),
            str(tmp_path / "synthetic.db"),
        ],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(root), "ENV": "development"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
