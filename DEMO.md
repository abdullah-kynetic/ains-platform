# Kien demo: one complete audit, start to finish

Synthetic data only. Real backend, real database tables (a throwaway SQLite file), no mocks.
Takes 5 to 15 minutes by hand, about 1 minute headless.

## Run it

| Command | What it does |
| --- | --- |
| `scripts/demo.sh test` | Runs steps 1 to 7 below in a headless browser from a clean database and reports pass or fail. Same as `cd web && npm run test:e2e:live`. |
| `scripts/demo.sh serve` | Starts a clean seeded backend and the web app so you can click through. Auditor sign-in: `http://kynetic.localhost:3100/sign-in`. |
| `scripts/demo.sh code` | Prints the current six-digit code the synthetic auditors need at sign-in. |

Needs the Python venv (`uv sync --frozen`), `npm ci` in `web/`, and Chromium for the headless run (`npx playwright install chromium`, or set `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` to an installed Chromium).
The synthetic users, password and one-time-code seed are test-only constants at the top of
`scripts/e2e_backend.py`. Nothing here talks to a real server, sends email, or uses real documents.

People in the demo (all synthetic, one practice):

- **Quentin** (partner): the assigned auditor, and the one who signs.
- **A second reviewer**: approves the file. The reviewer and the signing partner must be different people.
- **A client contact**: created by the invitation in step 1.

## Walkthrough

1. **Onboard a client.** Auditor: Clients, Add client workspace. Enter a firm name and review period, then create the workspace. Copy the client portal name and invite a contact. Preview mode shows the one-time link instead of sending email. Open it as the client and set a password.
2. **Send the checklist.** Auditor: engagement Overview, "Send checklist to client". The client now sees 34 numbered requests.
3. **N/A with a reason.** Client: Checklist, "Does not apply" on a request, with a reason. Auditor: Client checklist tab, approve one and reject one (a rejection needs a note).
4. **Upload and map.** Client: Upload, drop files and confirm. Each is numbered (1.1, 1.2 …). Checklist: map documents to requests, submit them. Auditor: Client checklist tab, "Accept for testing".
5. **Flag and respond.** Auditor: "Flag a problem" on a submitted request (for example "outdated"). Client: Messages, reply. Auditor: reply or mark resolved. Clients only ever see document notes and requests the auditor writes. They never see findings.
6. **Report, confirmation, invoice.**
   - Auditor: Checklist tab, give every request a conclusion. Independence tab, answer all five questions.
   - Second reviewer: Sign-off tab, "Approve as second reviewer".
   - Quentin: Sign-off tab, tick the box, type your full name, "Sign report", then "Mark complete".
   - Client: Report, "Confirm I received this report". Only then can an invoice be issued.
   - Auditor: Invoices, new invoice for the engagement, mark it sent. Client: Invoices shows it.
7. **Isolation and audit log.** Auditor: Isolation proof, "Run isolation check". Every request for another firm's data must be refused and your own data must still load. Audit Log: pick the firm, filter by `report.confirmed` or `signoff.reviewed`, then "Verify chain".

## What proves isolation

- Screen: `/auditor/isolation` makes live requests with an id that belongs to no firm you are assigned to.
- Tests: `tests/test_two_practice_isolation.py` builds two practices and two firms and calls every auditor and client route with the other side's real ids. Each new route also has its own cross-tenant test.

## Known limits (see `docs/handoff/LANE-1-HANDOFF.md`)

- Skipped by design: live email, card payments, real data, the AI items, secrets rotation doc, incident one-pager, audit-log checkpoint, invoice reminder emails.
- The headless run sets conclusions 2 to 34 and creates the invoice through the API for speed. Those screens exist and are what you use by hand.
- The questionnaire still has an older direct N/A path that differs from the reasoned N/A flow in step 3. Needs a decision.
- Finding response requests (auditor releases a finding as a request, client answers) are wired to the real routes but have no browser test yet.
