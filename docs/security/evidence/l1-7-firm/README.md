# L1-7 firm settings contracts

Synthetic local FastAPI/SQLite and Chromium only. These captures compare the
mock-backed pages on `main` with this branch's live-mode contract states at
desktop 1280×900 light/dark and phone 390×844. No real firm data appears.

The firm backend routes are not merged. Live mode therefore shows the typed
"Not available yet" error with retry and never reads or writes browser seed
data. Team, branding, rubric and template mutations retain form values after an
error and disable conflicting controls while a request is pending.

Branding now sends logo bytes as multipart field `file` to
`POST /auditor/firm/branding/logo`. The contract returns an HTTPS or
same-origin `logoUrl`; live mode rejects data URLs, protocol-relative URLs,
credentials, backslashes and malformed URLs. The saved branding object contains
the URL only. Demo mode remains explicitly synthetic and may use a data URL.

The live browser specs cover the absent-route state and client redirection.
Successful CRUD, invitation delivery, object storage, ownership checks,
last-partner protection and partner rubric approval remain BLOCKED(Lane 2) and
are not claimed by this evidence.

Verification on this candidate:

- Backend: 493 passed, 12 skipped; Ruff passed.
- Web lint and typecheck passed; 40 unit tests passed.
- Real-backend browser suite: 21 passed, including the three firm flows.
- Independent review: PASS; it reran 40 unit tests, 63 focused Python tests,
  Ruff, lint and typecheck.
- Local pip-audit, npm audit, Gitleaks, TruffleHog, Bandit and offline Zizmor
  passed. Hosted CI and all Security jobs are required before merge.
