# SOP — Deploy and rollback

Never deploy, migrate production or delete data without authorization for that task. Live frontend changes need Abdullah's visual approval.

> **Reference only for a separately authorized operation.** The current build request authorizes no deployment, server access, production migration or merge. Restore web auth before any live deployment or real data. Historical examples below do not establish current deployed state.

## Backend (OVH, `/opt/kien`, compose project `kien`)
Historical delivery pattern (unverified against current runtime):
1. Only after Abdullah says "go", and never by an agent on its own: connect to the Kien VPS (135.148.219.175; connection details are not kept in the repo; never print keys). Never use the old shared server 40.160.150.91. Work only in `/opt/kien`.
2. **Back up the DB first** (even with no migration):
   `docker exec <kien postgres container> pg_dump -U kien -d kien -Fc > /opt/kien/kien-db-<tag>-$(date +%Y%m%d%H%M%S).dump` then `pg_restore --list` on it to validate. Files are mode 600.
3. Record current image tag (e.g. `kien-api:pre-<tag>`), build the new image: `docker build -t kien-api:<tag> ...` from the pushed commit (source kept under `/opt/kien/src`, `DEPLOYED_COMMIT` file).
4. Write two override files: `deploy-<tag>.yml` (new image) and `rollback-<tag>.yml` (previous image).
5. Deploy: `docker compose -p kien -f docker-compose.yml -f deploy-<tag>.yml up -d --no-deps --no-build api`. The entrypoint runs `alembic upgrade head`.
6. Verify `/health`, then sign in with both demo logins (client + auditor roles).
7. **Rollback:** `docker compose -p kien -f docker-compose.yml -f rollback-<tag>.yml up -d --no-deps --no-build api`. Image rollback is safe only if the schema is compatible (migrations are additive). For destructive issues restore the dump with `pg_restore` into the kien database (ask first).
Examples on record: `kien-api:na-447e7f2` with `rollback-na-447e7f2.yml`, backup `/opt/kien/kien-db-na-20261026113037.dump`; onboarding `deploy-onboarding-02c480c.yml` / `rollback-onboarding-02c480c.yml`.

## Frontend (Cloudflare Workers, from `web/`)
- Preview: build with production API (`npm run build:cloudflare:production` or the configured preview build) and `wrangler deploy -c wrangler.preview.jsonc` → `kien-signin-preview`.
- Layout preview: `-c wrangler.layout.jsonc` → `kien-shadcn-preview`.
- Live: `kien-demo-live` — only after approval (exact live config/flags **unverified** in repo; `wrangler.jsonc` says `ains-platform-demo`).
- Before deploying: `wrangler deployments list -c <config>` and note the current version ID.
- **Rollback:** `wrangler rollback <version-id> --name <worker> -c <config>`.
  - Historical preview `kien-signin-preview` = `7e79cfa4…` (previous `e5c48f9c-776e-4a81-b550-136a9482743f`).
  - Historical layout `kien-shadcn-preview` = `8142b130-5c16-4da0-a2ac-ec999d64a874`.
- Verify the address loads, both demo logins work, light/dark/phone screenshots.

## Going live (after approval)
1. Merge stacked PRs to `main` in order with real merge commits.
2. Backend: deploy `main` image (usually already running the same code).
3. Frontend: deploy `main` to `kien-demo-live`; note previous version for rollback.
4. Verify with both demo logins; report to Abdullah.

## AWS (future)
`docs/deploy-aws.md` + `infra/aws` Terraform describe a single t4g.micro host. Do not apply without a separately approved plan and configured short-lived access; never request credentials or sign-in codes in chat.
