# Kien status (2026-11-09)

This page is the current status summary. It was checked against GitHub on 2026-11-09. Where a line says "not run", that check was not run.

## Where things stand

- **Code on `main`:** PRs #78 to #88 are merged. Web sign-in is restored (real `/auth/*` routes). Only the synthetic demo build (`NEXT_PUBLIC_USE_MOCKS=true`) skips sign-in.
- **Real client data:** none. Synthetic data only. The rule stays until the readiness checklist is complete and Abdullah changes it in writing. See [readiness checklist](readiness/readiness-checklist-2026-11-07.md).
- **AI:** the separate `ai_adapter/` skeleton exists on main, is off, and has an empty allowlist. The engine and adapter are frozen until Stage 2 sign-off. No model calls in Stage 1. Rule 10 and readiness item 41 disagree about OpenRouter approval; see [open questions](kb/19-open-questions.md).
- **Hosting plan (Abdullah, 2026-11-09):** one production Worker (`ains-platform`) and one API until pilot-ready. Existing preview/demo Workers are frozen; preview-first is paused. Lane C owns the new VPS; code agents have no server access. Source configuration does not prove deployment.
- **Mock gap:** many screen contracts still use the typed mock layer and browser storage, including firm settings. Production must not fall back to mocks. Lane 2 builds backend contracts and Lane 1 wires them; see [frontend inventory](frontend-inventory.md) and [build plan](BUILD-PLAN.md).
- **Gates:** G1 requires every Stage 1 acceptance item with evidence; G2 requires the Stage 2 security audit and Abdullah's written sign-off; G3 starts the engine only after G2. Real client data additionally requires all 45 readiness items and Abdullah's written authorization.
- **Deployments:** none were made in this cleanup.

## Test results

Quoted exactly as PR #84 states them:

- Normal suite: **339 passed + 1 skipped**.
- PostgreSQL 16.15: **11 tests run** on real PostgreSQL. These are not part of the normal suite.
- **CI now has a PostgreSQL 16 service** (`.github/workflows/ci.yml`, throwaway CI-only credentials, `KIEN_TEST_POSTGRES_URL`). The 11 PostgreSQL tests run on every pull request, each on a fresh database, and a CI step fails if any of them is skipped. Counts from the first CI run are recorded in the PR that added this.

Other runs recorded in the evidence files use different counts, for example 350 passed + 1 skipped on b6de342 in [checkpoint-TEST-4](evidence/testing/checkpoint-TEST-4.md). Those runs were on other candidates. Do not mix the counts. Quote the #84 numbers unless a run is re-done and recorded.

The raw PostgreSQL console output was not kept in the sandbox. What remains is the summary in the checkpoint files, linked below. The drill results are the raw per-check TSV files.

## Backup restore drill

The drill ran 27 checks on several candidate commits. Results are in the TSV files:

- [drill-results-b6de342.tsv](evidence/testing/drill-results-b6de342.tsv): 27/27 PASS as shipped. This is the final result.
- [drill-results-89d925f.tsv](evidence/testing/drill-results-89d925f.tsv) and [drill-results-89d925f-with-D9-patch.tsv](evidence/testing/drill-results-89d925f-with-D9-patch.tsv): earlier runs.
- [drill-results-b2cd6ae.tsv](evidence/testing/drill-results-b2cd6ae.tsv): first run, 26 PASS and 1 FAIL (defect D1, since fixed).

The drill used a software S3 stand-in (moto), not real R2, and a `docker` stand-in. It is emulator coverage only. Not run: real R2, object-lock drill, Docker build, Caddy, systemd, ClamAV, OpenRouter.

## Evidence in this repo

- [docs/evidence/testing/](evidence/testing/): drill TSVs, checkpoint notes TEST-1 to TEST-4, verify reports 1, 2, 4, 5, 6, 7.
- [docs/evidence/research/public-aml-test-data-sources.md](evidence/research/public-aml-test-data-sources.md): AML test-data research. Nothing was built or scraped from it.
- [docs/readiness/readiness-checklist-2026-11-07.md](readiness/readiness-checklist-2026-11-07.md): the 45-item readiness checklist.
- Not committed on purpose: the `handoff/*.bundle` files, the planning documents in `plans/`, and scratch probe and patch files. They stay in the project files.

## Open pull requests (triage, 2026-11-09)

Ten PRs were open. Actions taken or proposed:

| PR | Title | Decision | Reason |
| --- | --- | --- | --- |
| #1 | Client progress and auditor review frontend | Keep | 23 commits and no merge base with `main`; built on an October 21 branch. Review against the current frontend before any rebuild. |
| #37 | Configure portal API URL | Keep | Most of it is on `main` (credentials, env-driven CORS, production build script). Still open: production API URL default and Wrangler production vars. Rebuild on `main` first. |
| #39 | Synthetic Postgres backup restore drill | Close as superseded | `main` already has the restore drill (`deploy/backup/restore-drill.sh`, from b6de342), with 27/27 results above. |
| #40 | Resend mail for reset and report-ready | Keep | Invitations already send via Resend on `main`. Password reset and report-ready mail exist only here. Needs a rebuild on `main`. |
| #41 | Public landing page | Keep | Not on `main`. Public site: needs Abdullah's review before any deploy. No DNS touched. |
| #45 | Firm portals on slug subdomains | Keep | Tenant branding and slug hosts are not on `main`. The rebuild changes Terraform and DNS, which are on hold with the VPS. |
| #50 | Apple-style polish (draft) | Keep, decision needed | Ochre active pill and extra ochre accents conflict with the approved neutral look in `DESIGN.md`. Abdullah to decide: likely close. |
| #62 | Design skills and a11y tooling | Keep | Playwright and axe a11y config is not on `main`. About 210 third-party skill files need review first. |
| #63 | Maroon accent palette (preview only) | Keep, decision needed | Conflicts with the approved neutral look. Design experiments go on a separate address (rule 7). Abdullah to decide: likely close. |
| #73 | Page titles, 404 page, no em dashes | Keep | 404 page and titles are not on `main`. Needs a rebase on `main`. |

Only #39 was closed. Rebuilds were not started: #40, #45 and #37 each need their own branch and PR, and the coordinator asked that rebuilt PRs be listed rather than merged.

## Open decisions for Abdullah

1. Whether #50 and #63 are closed.
2. Whether #40, #45 and #37 are rebuilt on `main` now, or after the VPS phase resumes.
3. The partner-firm conflict in [VISION.md](VISION.md) needs legal and commercial advice before any decision.
4. The items in the readiness checklist marked for Abdullah, starting with Phase 0.
