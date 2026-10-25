# Kien Solutions web (client portal)

Next.js 16 (App Router, TypeScript) + Tailwind v4. Talks to the Kien Solutions FastAPI backend at `NEXT_PUBLIC_API_URL`.

```bash
cd web
cp .env.example .env.local   # NEXT_PUBLIC_USE_MOCKS=true serves synthetic demo data
npm ci
npm run dev                  # http://localhost:3000
npm run lint && npm run typecheck && npm run build
```

- `src/lib/checklist.ts`: client statuses (same values as `app/checklist.ClientStatus`), labels, progress helpers.
- `src/lib/api.ts`: typed API client for backend sessions, engagements, questionnaire answers, uploads, auditor review, and draft report downloads.
- `src/lib/mock-data.ts`: synthetic engagement only.
- `src/components/ui`: shared UI primitives; `src/components/checklist`: checklist, status badge, drag-and-drop upload with progress.
- `/sign-in`: invite-only password or magic-link sign-in; auditor accounts also provide MFA.
- `/questionnaire`: client yes/no applicability questions. N/A answers remain pending until Quentin decides them.
- `/auditor`: auditor-only engagement queue, evidence/check results, cited finding review, and unsigned report drafts.

The default `.env.example` has `NEXT_PUBLIC_USE_MOCKS=false`. The FastAPI backend must be running
at `NEXT_PUBLIC_API_URL`, with an invited user in Postgres and `SESSION_SECRET` configured.
Magic-link delivery still requires an approved backend email adapter; password sign-in works
without that adapter. Never place credentials in a `NEXT_PUBLIC_*` variable.

## Cloudflare synthetic demo

The `ains-platform-demo` Worker serves the client and auditor workflow demo at
https://ains-platform-demo.ains-web.workers.dev. This deployment always builds with
`NEXT_PUBLIC_USE_MOCKS=true`; it does not deploy FastAPI, Postgres, real sign-in or
S3 or optional Egnyte ingestion. Demo receipts and decisions stay in browser storage. Use synthetic
files only and use the labeled demo role switch to inspect the auditor workspace.

```bash
npm ci
npm run build:cloudflare
# With CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID supplied by the environment:
npm run deploy:demo
```

`deploy:demo` rebuilds before publishing, so stale API-mode output cannot be deployed
by that command. Cloudflare runs the OpenNext adapter with Node compatibility; generated
`.open-next` and `.wrangler` artifacts are ignored. Never add deployment tokens to files.

To test the packaged Worker locally, run `npx wrangler dev --port 8787`, then in another
terminal run `PLAYWRIGHT_BASE_URL=http://127.0.0.1:8787 npm run test:e2e`.
`PLAYWRIGHT_BASE_URL` skips Playwright's development server and targets the supplied
synthetic demo instead. CI also builds the Cloudflare bundle to catch adapter regressions.

### Production on Cloudflare Workers

Use a custom portal domain under the same parent domain as the API (for example,
`portal.example.com` and `api.example.com`) so secure backend session cookies work.
`NEXT_PUBLIC_API_URL` is a **public build-time** setting, not a secret. Set it to
`https://api.example.com` before building; changing a Wrangler runtime variable does
not replace a URL already embedded in browser JavaScript.

```sh
export PATH="$HOME/.local/node22/bin:$PATH"
NEXT_PUBLIC_API_URL=https://api.example.com npm run build:cloudflare:production
npx opennextjs-cloudflare deploy --env production
```

Configure the custom domain for the production Worker in Cloudflare before publishing;
production disables `workers.dev`. The production build forces mocks off; demo builds
retain their existing synthetic behavior. Do not use `deploy:demo` for production.
See [the AWS deployment runbook](../docs/deploy-aws.md) for backend, CORS, DNS and secrets.

## Optional Sentry error monitoring

Sentry free plan -- optional; leave DSNs blank to disable it entirely. No Sentry
account, auth token or source-map upload is required to build or deploy.
Backend settings: `SENTRY_DSN` (blank by default), `SENTRY_ENVIRONMENT` (default
`production`), `SENTRY_TRACES_SAMPLE_RATE` (0 by default; range 0–1). Supply backend
settings through the deployment environment and restart the API. Browser monitoring
uses `NEXT_PUBLIC_SENTRY_DSN`, a public build-time DSN; rebuild the portal after
changing it. Never put a Sentry auth token in public variables.

The browser-only `@sentry/browser` SDK runs through Next.js client instrumentation
and is compatible with OpenNext/Cloudflare Workers without a server SDK or build
plugin. It captures uncaught browser errors; Worker/server-render errors are not
captured. Backend FastAPI exceptions use `sentry-sdk[fastapi]`.

Both scrubbers rebuild events from a strict allowlist: a fixed error label and
numeric stack line/column locations only. Request bodies, cookies, headers, URLs,
users/emails, exception messages, source/locals, breadcrumbs, tags, custom context,
document metadata/content and SAR data are discarded, including unknown fields.
This intentionally limits diagnostic detail and grouping. PII, session tracking,
replay, logs and trace propagation are disabled. Backend transaction events are
always dropped for privacy, even if a nonzero trace sample rate is configured.
Source maps are neither generated for Sentry nor uploaded. Use only synthetic data
when checking delivery; do not add attachments or alternate telemetry transports.
