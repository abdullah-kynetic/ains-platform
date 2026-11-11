"""Local backend for the web sign-in end-to-end test. SYNTHETIC data and test-only secrets.

Starts the real FastAPI app on a throwaway SQLite file with a few synthetic users, so the
browser test exercises the real /auth/* routes. Never point this at a real database.

    uv run python scripts/e2e_backend.py [--port 8000] [--db /tmp/kien-e2e.db]
"""

import argparse
import hashlib
import os
import shutil
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

PORT_DEFAULT = 8000
FIRM_SLUG = "kynetic"
ORIGIN = f"http://{FIRM_SLUG}.localhost:3100"
CLIENT_PASSWORD = "synthetic-client-password"
AUDITOR_PASSWORD = "synthetic-auditor-password"
INVITE_TOKEN = "synthetic-invitation-token-0123456789abcdef"
# Second, independent practice for the demo journey (web/e2e-live/demo-journey-live.spec.ts):
# the assigned auditor (also a partner) and a separate reviewer, as sign-off requires.
DEMO_PRACTICE = "Synthetic Demo Practice"
DEMO_USERS = {
    "auditor": ("e2e-quentin@example.test", "Synthetic Quentin", "partner"),
    "reviewer": ("e2e-reviewer@example.test", "Synthetic Reviewer", "reviewer"),
}
USERS = {
    "client": "e2e-client@example.test",
    "lockout": "e2e-lockout@example.test",
    "auditor": "e2e-auditor@example.test",
    "invitee": "e2e-invitee@example.test",
}


def configure(db_path: Path) -> None:
    # Browser flows share one loopback IP; keep their aggregate traffic below a finite
    # test-only limit. Account lockout remains enabled; this is not rate-limit proof.
    os.environ["API_RATE_LIMIT_PER_MINUTE"] = "1200"
    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path}"
    os.environ["SESSION_SECRET"] = "synthetic-e2e-session-secret-not-for-real-use-0000"
    os.environ["SESSION_COOKIE_SECURE"] = "false"
    os.environ["CORS_ORIGINS"] = ORIGIN
    # One-time invitation links are returned to the auditor instead of emailed (no live email).
    os.environ["INVITATION_PREVIEW_ENABLED"] = "true"
    os.environ["ISOLATION_PROBE_ENABLED"] = "true"
    os.environ["PORTAL_URL"] = ORIGIN


def seed() -> None:
    from sqlalchemy import select

    from app.auth.security import hash_invitation_token, hash_password
    from app.checklist.catalog import initialize_engagement
    from app.database.models import (
        AuditLog,
        Base,
        ClientInvitation,
        Document,
        Engagement,
        Firm,
        Practice,
        User,
        UserRole,
    )
    from app.database.session import get_engine, get_session_factory

    Base.metadata.create_all(get_engine())
    now = datetime.now(UTC)
    with get_session_factory()() as db:
        firm = Firm(name="Synthetic E2E Securities", slug=FIRM_SLUG)
        db.add(firm)
        db.flush()
        auditor = User(
            email=USERS["auditor"],
            name="Synthetic E2E Auditor",
            role=UserRole.AUDITOR,
            password_hash=hash_password(AUDITOR_PASSWORD),
            accepted_at=now,
        )
        db.add(auditor)
        practice = Practice(name=DEMO_PRACTICE, allow_auditor_as_signer=True)
        db.add(practice)
        db.flush()
        for email, name, team_role in DEMO_USERS.values():
            db.add(
                User(
                    email=email,
                    name=name,
                    role=UserRole.AUDITOR,
                    password_hash=hash_password(AUDITOR_PASSWORD),
                    accepted_at=now,
                    practice_id=practice.id,
                    team_role=team_role,
                )
            )
        for key in ("client", "lockout"):
            db.add(
                User(
                    firm_id=firm.id,
                    email=USERS[key],
                    name=f"Synthetic E2E {key.title()}",
                    role=UserRole.CLIENT,
                    password_hash=hash_password(CLIENT_PASSWORD),
                    accepted_at=now,
                )
            )
        db.flush()
        engagement = Engagement(
            firm_id=firm.id,
            auditor_id=auditor.id,
            due_date=date.today(),
            review_period_start=date(2025, 1, 1),
            review_period_end=date(2025, 12, 31),
        )
        db.add(engagement)
        db.flush()
        initialize_engagement(engagement)
        db.flush()
        client = db.scalar(select(User).where(User.email == USERS["client"]))
        item = next(item for item in engagement.items if item.item_key == "AML-BD-001")
        # Receipt metadata only: these review tests do not claim upload or storage proof.
        document = Document(
            firm_id=firm.id,
            engagement_id=engagement.id,
            item_instance_id=item.id,
            uploaded_by_id=client.id,
            original_name="synthetic-review-policy.pdf",
            content_type="application/pdf",
            size_bytes=28,
            egnyte_path="/synthetic-e2e/receipt-only/policy.pdf",
            sha256=hashlib.sha256(b"synthetic-review-policy").hexdigest(),
        )
        db.add(document)
        db.flush()
        db.add(
            AuditLog(
                firm_id=firm.id,
                actor_id=client.id,
                action="document.created",
                entity_type="checklist_item_instance",
                entity_id=item.id,
                details={"document_id": document.id},
            )
        )
        other_firm = Firm(name="Synthetic Other Firm", slug="synthetic-other")
        db.add(other_firm)
        db.flush()
        other_engagement = Engagement(
            id="synthetic-other-engagement",
            firm_id=other_firm.id,
            review_period_start=date(2025, 1, 1),
            review_period_end=date(2025, 12, 31),
        )
        db.add(other_engagement)
        db.flush()
        initialize_engagement(other_engagement)
        db.add(
            ClientInvitation(
                firm_id=firm.id,
                engagement_id=engagement.id,
                email=USERS["invitee"],
                name="Synthetic E2E Invitee",
                token_hash=hash_invitation_token(INVITE_TOKEN),
                expires_at=now + timedelta(days=3),
                created_by_id=auditor.id,
            )
        )
        db.commit()


class LocalReceiptIngestor:
    """Test-only document store: synthetic files go to a throwaway folder beside the SQLite file.

    Production stores files in R2 (S3DocumentIngestor). Validation (name, type, size) is the
    production code's own; malware scanning is off here as it is in every local run.
    """

    def __init__(self, folder: Path) -> None:
        self.folder = folder

    async def ingest(self, *, engagement, item, file):
        import uuid

        from fastapi import HTTPException

        from app.documents.ingestion import (
            ALLOWED_EXTENSIONS,
            StoredDocument,
            _read_validated,
            _validated_filename,
        )

        if item and (item.firm_id != engagement.firm_id or item.engagement_id != engagement.id):
            raise HTTPException(status_code=404, detail="Checklist item not found")
        if item and item.restricted:
            raise HTTPException(status_code=422, detail="Restricted uploads are not accepted")
        name, suffix = _validated_filename(file.filename)
        accepted = {
            f".{ext.lstrip('.').casefold()}"
            for ext in (item.accepted_extensions if item else ALLOWED_EXTENSIONS)
        }
        if accepted and suffix not in accepted:
            raise HTTPException(status_code=415, detail="File type is not accepted")
        content, digest = await _read_validated(file, suffix)
        target = self.folder / engagement.firm_id / f"{uuid.uuid4().hex}-{name}"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return StoredDocument(
            egnyte_path=f"local://{target.relative_to(self.folder)}",
            sha256=digest,
            size_bytes=len(content),
        )


def serve(port: int, files: Path) -> None:
    """Run the real app with the local receipt store; one request at a time (SQLite)."""
    import anyio.to_thread
    import uvicorn

    from app.documents import get_document_ingestor
    from app.main import app

    async def one_request_at_a_time() -> None:
        # SQLite has no advisory lock, so concurrent audit-log appends can pick the same sequence
        # number (production PostgreSQL serialises them in app/audit.py). One worker thread keeps
        # this throwaway backend faithful without touching production code.
        anyio.to_thread.current_default_thread_limiter().total_tokens = 1

    ingestor = LocalReceiptIngestor(files)
    app.dependency_overrides[get_document_ingestor] = lambda: ingestor
    app.router.on_startup.append(one_request_at_a_time)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=PORT_DEFAULT)
    parser.add_argument("--db", type=Path, default=Path("/tmp/kien-e2e.db"))
    args = parser.parse_args()
    if "postgres" in os.environ.get("DATABASE_URL", ""):
        sys.exit("Refusing to run: DATABASE_URL points at Postgres. This script is synthetic-only.")
    args.db.unlink(missing_ok=True)
    files = args.db.with_suffix(".files")
    shutil.rmtree(files, ignore_errors=True)
    configure(args.db)
    seed()
    serve(args.port, files)


if __name__ == "__main__":
    main()
