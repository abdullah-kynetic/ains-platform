# Stale workflow branch port

Compared `origin/main...origin/codex/frontend-review-workflow` and read selected stale
files using `git show`. No wholesale cherry-pick, merge, remote changes, or push.

## Ported

- Session issuance and decoding reject secrets shorter than 32 UTF-8 bytes.
- `/auth/capabilities` exposes configured password and email sign-in methods;
  the default unconfigured email adapter returns 503 for magic-link requests.
- Auth readiness tests and deployment documentation, updated to acknowledge main's
  invitation and MFA enrollment/recovery implementations.
- Checklist initialization stores a catalog version and JSON snapshot as provenance,
  with version metadata in creation/initialization audit events. The migration follows
  `a108_auditor_mfa_recovery`, rather than the stale branch's older head. Existing
  engagements remain nullable; no invented historical snapshot is backfilled.
  Main's canonical catalog continues to govern rendering and workflow rules.
- Client progress route and navigation, using current engagement state, neutral intake
  statuses, accessible progress labels, and the existing retry component.
- Demo catalog parity test adapted to `.generated/catalog.json`, and a synthetic-only
  progress browser test that checks accessibility and absence of backend calls.

## Skipped

- AI provider citation checks and automatic review-period status decisions: these
  depend on removed inference/extraction code. Main deliberately verifies storage
  receipts only and requires human document judgments. Existing manual finding
  citation requirements remain intact.
- Stale onboarding router, instances helper, manage screen, and engagement workspace:
  main has `/auditor/workspaces`, `initialize_engagement`, audited pipeline stage
  transitions, follow-up release, invitations, and the manual auditor workspace.
  Preserve those implementations rather than add a competing onboarding flow.
  The stale separate approve/publish interface is not introduced; main's audited
  pipeline stage transition remains its engagement-state control.
- `demo.ts` and checked-in `demo-catalog.json`: main already has persistent synthetic
  workflow adapters and generates the web catalog from the authoritative YAML.
  The old catalog shape and seeded finding examples must not replace current data.
- Old demo browser selectors/workflows: main already tests workspace invitations,
  auditor decisions, uploads, tasks, activity, pipeline, and accessibility. The added
  demo test covers the newly ported progress route using current navigation.

## Validation in this environment

Web lint and typecheck pass. Ruff and focused catalog/auth unit tests pass.
The full pytest command stalls entering Starlette TestClient's AnyIO blocking portal
(before application requests); a bounded diagnostic reproduced that startup stall.
Default Next.js build fails because the sandbox denies Turbopack local port binding;
webpack fallback fails parsing TypeScript `--showConfig`. Playwright cannot start its
web server in this sandbox. These checks must run in an environment allowing the
required processes and local sockets before merge.

Logical commits intended: authentication readiness; checklist provenance migration;
client progress and synthetic demo parity. Git staging/commits are blocked here:
`.git/index.lock` cannot be created on the read-only `.git` mount.
