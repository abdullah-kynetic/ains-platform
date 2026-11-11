# Live demo run

**Status: not run.** No live run exists yet, so there is no time and no result to report. The deploy
(`docs/demo/DEPLOY-DEMO.md`) needs a person with SSH to the VPS and Cloudflare credentials.

## What was verified instead (local, real backend, synthetic data)

`scripts/demo.sh test` runs the whole `DEMO.md` walkthrough headless on the real FastAPI backend with a
throwaway SQLite database: 9 of 9 passed, about 1.4 minutes of automated time (not a human timing).
That includes a real second firm on the isolation screen and a check that the browser reported no
Content-Security-Policy violation. It says nothing about the live server, Postgres, Caddy, Cloudflare,
the malware scanner or email.

## Fill in after the live run

Target: 5 to 15 minutes by hand, no errors.

| Step | What | Minutes | Result |
|---|---|---|---|
| 1 | Onboard a client (or use the seeded contact) | | |
| 2 | Send the checklist | | |
| 3 | N/A with a reason, approve and reject | | |
| 4 | Upload, map, submit, accept | | |
| 5 | Flag a problem, reply, resolve; finding response request | | |
| 6 | Conclusions, independence, review, sign, confirm, invoice | | |
| 7 | Isolation check and audit log chain | | |
| | **Total** | | |

Date, who ran it, commit and image digest:

Errors seen (exact text, no secrets):
