# Open questions

## Decisions needed from Abdullah

- Stripe account/entity, payment methods and treatment of fees; implementation uses test mode only with payments disabled by default.
- AWS architecture (single host or managed database), account/region confirmation, spending cap and resource inputs. Do not request sign-in codes or credentials in chat.
- Backup RPO/RTO, off-site destination, retention/deletion and legal hold policy.
- Security owner and product success targets. Abdullah Ahmed is the product owner.
- Auditor hostname and any Cloudflare Access policy before auth rollout.
- Whether to retain the current behavior allowing a client to undo auditor-marked N/A; preserve it pending a decision.

## Needs Quentin

Rubric wording, applicability and allowed evidence for all 34 requests; severity logic; report template and sign-off procedure. Leave unapproved rubric criteria empty. Synthetic examples only.

## Needs attorney

Privacy/terms wording, Reg S-P obligations and incident terms; any future model-provider/data-retention approval is outside this task. Do not invent legal text.

## Unverified operational facts

Current deployed Worker/version/bindings, live Sentry state, backup schedule and restore evidence were not inspected. `/tenant/branding` has a frontend client but no backend route found in source. OVH is current per the owner; AWS is planned. Source merged status does not prove deployment.

## Readiness item 41 versus rule 10 (unresolved)

Readiness item 41 says "OpenRouter is not approved for client data; synthetic only."
`CLAUDE.md` rule 10 says attorney sign-off covers approved vendors directly or via
OpenRouter, including real client data. These statements conflict; source text is
not evidence resolving the scope of legal approval. BLOCKED(owner/attorney): confirm
and reconcile the written approval and readiness item 41. Until then use synthetic
data only, make no model calls in Stage 1, and preserve the G1/G2/G3 gates. No paid
fallback; the existing OpenRouter balance remains untouched.
