# Synthetic Supabase PostgreSQL proof of concept

> **Archived decision record:** Supabase is not part of the planned Kien Solutions architecture. This
> synthetic evaluation is retained only to document what was considered. Do not run it, provision
> a Supabase project, configure credentials, migrate data or replace working Kien Solutions services.

This checkpoint uses Supabase only as hosted PostgreSQL. FastAPI continues to own sessions,
client invitations, password hashing, auditor MFA, workflow authorization, and tenant scoping.
Supabase Auth, Storage, Realtime, Edge Functions, and production data are out of scope.

## Create an isolated project

Create a new Supabase project containing synthetic data only. Prefer the session pooler connection
for the long-running FastAPI service when direct IPv6 connectivity is unavailable. Convert the
dashboard connection URI to SQLAlchemy's psycopg form and require TLS:

```text
postgresql+psycopg://postgres.PROJECT_REF:PASSWORD@POOLER_HOST:5432/postgres?sslmode=require
```

Store that value as `SUPABASE_POC_DATABASE_URL` in the environment's secret manager. Do not paste
it into tracked files, logs, chat, or a `NEXT_PUBLIC_*` variable. Permit outbound TCP only to the
selected Supabase database hostname and port.

The PoC command fails closed unless both variables are supplied:

```bash
SUPABASE_POC_SYNTHETIC_ONLY=true \
uv run python scripts/supabase_poc.py run
```

`run` refuses any target that already contains Kien Solutions application rows, applies the repository's
Alembic migrations, confirms the exact migration head, creates two synthetic firms inside a
transaction, verifies client firm isolation and auditor assignment scope, and rolls the entire
probe back. It never prints the connection URL. `migrate` and `verify` are available separately
for diagnosis.

## Run FastAPI against the validated project

After the PoC succeeds, set the backend-only `DATABASE_URL` secret to the same connection URI and
start FastAPI normally. Do not configure Supabase browser keys: the web application continues to
call FastAPI, and the Cloudflare demo remains mock-backed.

Before any production evaluation, separately review connection limits, backups, point-in-time
recovery, data residency, credential rotation, monitoring, and a tested rollback plan. Moving real
data or replacing backend authentication requires its own approved checkpoint.
