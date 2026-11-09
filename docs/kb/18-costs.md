# Costs (all figures are ESTIMATES unless marked)

Principle: as cheap as possible; use free tiers and existing infrastructure.

| Item | Today | Estimate |
| --- | --- | --- |
| Cloudflare Workers (4 Workers) | Free / Workers Paid if needed | $0–5/mo |
| Cloudflare R2 | Low volume | $0 (free tier 10 GB) |
| OVH VPS | Shared with other services | Existing cost (not tracked here — unverified) |
| Resend | Low volume | $0 (free tier) |
| GitHub + Actions | Private repo | $0 within free minutes (assumed) |
| Sentry | Free plan, optional | $0 |
| Domain kiensolutions.com | Annual | ~$10–20/yr |
| Codex / ChatGPT plan | Owner's existing plan | Existing |
| Claude Pro | Owner's existing plan | Existing |
| Notion | Free for now | $0 |

## After AWS move (single-host profile, estimates)
t4g.micro EC2 ~$6/mo, 20 GB gp3 ~$2, Elastic IP (attached public IPv4) ~$3.6, S3 small, CloudTrail first trail free, SSM Parameter Store standard free → roughly **$12–15/mo** before credits (budget alarm $15 in repo). RDS adds ~$15+/mo when justified. Startup credits (Kynetic AWS credits application) may cover this.

## AI (planned, estimates)
Chatbot: cents to embed rules; a few $/mo for answers at low volume. Intake sorting: depends on pages processed; estimate before building.

## Stripe (later)
Per-transaction fees only (standard card pricing); behind a flag.
