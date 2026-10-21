# AINS web (client portal)

See [frontend scope](FRONTEND_SCOPE.md) for the meeting-driven client progress, auditor dashboard,
processing, summary/review, feedback, report-readiness, and theme screens, plus the MCP boundary.

Cloudflare synthetic demo: set `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` in the deployment
environment, then run `npm run deploy:demo` from `web/`. This builds with mock data enabled and
publishes the `ains-platform-demo` Worker at its account's `workers.dev` address. Credentials stay
in the deployment environment; the demo needs no backend credentials. This displays client demo
pages with a clearly labeled client/auditor view switch. Review decisions, draft creation,
publication, and uploads are simulated in browser memory and reset on refresh. File bytes are
never read or uploaded in demo mode; report downloads require the authenticated backend.
The 34-request demo catalog is checked against the authoritative YAML by the backend test suite.

Next.js 16 (App Router, TypeScript) + Tailwind v4. Talks to the AINS FastAPI backend at `NEXT_PUBLIC_API_URL`.

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
- `/questionnaire`: client yes/no applicability questions. N/A answers remain pending until Quinton decides them.
- `/auditor`: auditor-only engagement queue, evidence/check results, cited finding review, and unsigned report drafts.

The default `.env.example` has `NEXT_PUBLIC_USE_MOCKS=false`. The FastAPI backend must be running
at `NEXT_PUBLIC_API_URL`, with an invited user in Postgres and `SESSION_SECRET` configured.
Magic-link delivery still requires an approved backend email adapter; password sign-in works
without that adapter. Never place credentials in a `NEXT_PUBLIC_*` variable.
