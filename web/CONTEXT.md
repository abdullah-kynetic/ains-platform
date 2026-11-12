# web - Next.js auditor and client app

One job: the browser UI. Role gates here are cosmetic; the API enforces access.

## Inputs
- Reference (every run): `AGENTS.md` (Next.js 16 differs from older versions; read `node_modules/next/dist/docs/` first)
- Reference (every run): `../DESIGN.md`
- Reference (every run): `../docs/DESIGN_SYSTEM.md`
- Reference (every run): `../docs/frontend-inventory.md`
- Working (this task): the file under `src/app/`, `src/components/` or `src/lib/api/`

Do NOT load: `../app/`, `../audit_engine/`.

## Process
1. Keep the neutral black-and-white look; no gradients, glass or cream.
2. Clients never see findings or AI drafts, only released "Responses requested".
3. Keep status values aligned with `app/checklist.ClientStatus`. No secrets in `NEXT_PUBLIC_*`.
4. Screens without a backend route use the typed mock layer marked `TODO(backend)`.

## Outputs
- Components and pages with unit tests; e2e specs in `e2e/` and `e2e-live/`.

## Check
In `web/`: `npm run lint`, `npm run typecheck`, `npm run test:unit`, `npm run build:cloudflare`; for flow changes `../scripts/demo.sh test`.
