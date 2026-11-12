# AI analysis smoke test (synthetic firm only)

Run this once after the AI service is deployed and switched on, and again before the Friday demo. Use only the synthetic demo firms. Never upload a real client file, and never type SAR material into a real file: the SAR step below uses a made-up phrase in a made-up file.

Pass means every line below is "as expected". Write the result next to each step. Stop at the first surprise and leave the switch off.

## Before the service is started (server operator)
| # | Check | As expected |
|---|---|---|
| P1 | `ip route` on the VPS | Nothing covers `10.77.40.0/24` (OVH or VPN setups sometimes use 10.x). If something does, stop and pick another subnet in `deploy/docker-compose.ai.yml` and `deploy/ai/egress-firewall.sh` |
| P2 | `docker compose ... config` with the overlay | Exits cleanly; `backend` is shared by Postgres and the API; existing memory limits unchanged |
| P3 | `deploy/ai/egress-firewall.sh` (dry run), then `--apply` as root | Rules printed first; DNS only to the host's resolvers; 443 only to openrouter.ai |
| P4 | After apply and `up`, from inside the adapter container: resolve `openrouter.ai`, then try any other host | openrouter.ai resolves and answers on 443; everything else is refused. If lookups fail, Docker's DNS differs from the host's resolvers: it fails closed, fix before switching on |

## Before you start
| # | Check | As expected |
|---|---|---|
| 0.1 | `https://api.kiensolutions.com/health` | `200` |
| 0.2 | AI service container is healthy (`docker compose ... ps ai-adapter`) | healthy |
| 0.3 | Sign in as a synthetic **auditor** assigned to a synthetic engagement; open **Findings** | The **AI analysis** panel and **Run AI analysis** button are visible |
| 0.4 | Sign in as a synthetic **client** | No AI panel, no drafts, no findings anywhere |

## A. Run
| # | Do | As expected |
|---|---|---|
| A1 | Upload one small synthetic text file (for example `alerts.txt`: "Monthly alert review was completed late in Q2.") against a checklist item | Upload accepted |
| A2 | Click **Run AI analysis** once | Button shows "Analysing…" and is disabled |
| A3 | Click it again, fast, while it is still running (or open a second tab and click there) | No second run starts: the second request gets a plain "already running" message (HTTP 409). Only one new run appears afterwards |
| A4 | Wait for the answer | "Last run: 1 file analysed with <model id ending in :free>". Drafts listed as **pending**, each naming a file and a page |
| A5 | Note which model ID is shown | Ends in `:free`. Anything else: stop |

## B. Review
| # | Do | As expected |
|---|---|---|
| B1 | **Accept** a draft | It becomes an ordinary **draft** finding in the Findings list, citing the file and page. It is not released to anyone |
| B2 | **Edit** another draft (change the text) and save | Text changes, marked edited. Accept it: the finding uses the edited text |
| B3 | **Reject** a third draft | It closes. No finding is created |
| B4 | Try to accept the same draft again (second tab) | Refused ("already accepted") |
| B5 | Sign in as the client | Still sees nothing from the AI. Only a finding you separately approve and release as a "Response requested" shows, and then without any AI label |

## C. SAR block
| # | Do | As expected |
|---|---|---|
| C1 | Upload a synthetic file named `notes.txt` containing only: "This memo discusses the Suspicious Activity Report filing for a made-up customer." | Upload accepted |
| C2 | Run AI analysis | The run lists `notes.txt` under **Skipped** with a SAR reason. No draft cites it |
| C3 | Optional: check the AI service log | No document text in it, only ids and outcomes |

## D. Firm isolation
| # | Do | As expected |
|---|---|---|
| D1 | As the auditor of firm A, note a draft id from the browser network tab, then sign in as the auditor of firm B and call that draft's accept route | `404` (not `403`, not the draft) |
| D2 | As firm B's auditor, open firm A's engagement URL | `404` |
| D3 | Run analysis in firm B | Only firm B's files are listed or analysed |

## E. Off switch
| # | Do | As expected |
|---|---|---|
| E1 | Set `AI_ANALYSIS_ENABLED=false` for the API and recreate `api` | The panel and button disappear for auditors; direct AI routes return `404` |

## Known limits to say out loud
Free-model quality is unmeasured; runs take as long as the model takes (up to 8 files per run); scans (no OCR), XLSX and DOC are skipped and listed; the daily free quota is 40 calls.
