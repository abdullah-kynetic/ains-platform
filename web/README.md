# AINS web (client portal)

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
