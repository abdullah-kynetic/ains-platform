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
- `src/lib/api.ts`: API client. Planned endpoints: `GET /engagements/current`, `POST /engagements/{id}/items/{itemId}/documents`. Until they exist, mocks are used.
- `src/lib/mock-data.ts`: synthetic engagement only.
- `src/components/ui`: shared UI primitives; `src/components/checklist`: checklist, status badge, drag-and-drop upload with progress.

Not wired yet: sign-in (will come from the API), auditor workspace.
