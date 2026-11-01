# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Independent AML auditors working with broker-dealers, and the broker-dealer client
users who supply documents and applicability declarations. Quentin is the AINS
partner and auditor who approves findings and signs reports. There is no distinct
firm-admin role in the application.

## Product Purpose

Kien by Kien Solutions organizes independent AML testing under FINRA Rule 3310.
It connects document collection, human evidence review, traceable decisions,
auditor report preparation and invoicing. Success means users can complete their
assigned workflow with a clear distinction between collection status and an audit
conclusion. The interface supports precision and restraint.

## Operating Context

Clients sign in to their firm portal, answer the questionnaire, upload documents,
review neutral document feedback and track collection progress. Auditors work
across server-authorized engagements, assess evidence, manage requests and tasks,
review internal history, prepare reports and explicitly approve final versions.
Desktop and phone use, keyboard navigation and light/dark/system preferences are
established requirements. Synthetic demos are explicitly labeled and separate
from real authentication, authorization, email, storage or payment operations.

## Capabilities and Constraints

- FastAPI owns authentication, firm ownership and auditor engagement assignment;
  browser role gates are usability controls. Demo role switching grants no access.
- The canonical YAML defines 34 stable request IDs. All remain numbered and
  visible; N/A sorts last, counts as resolved and can be undone by permitted users.
- Receipt checks verify stored metadata and integrity, not document sufficiency.
  Client feedback describes document issues, never audit findings.
- Findings remain drafts until human approval. Only an auditor can sign or finalize
  a report. Finalization records human approval, not a cryptographic signature.
- Restricted/SAR material is human-only and is not retained in ordinary notes or
  sent to models. No model inference or model credentials belong in the app.
- Invoices are auditor-only. Existing manual status/payment recording does not
  contact a payment processor or send email.
- Preserve existing routes, flows, permission checks and copy in refinement work.
  Use synthetic data only for tests, demonstrations and examples; never expose secrets.
- Audit rubric approval, retention policy, backup objectives and formal success
  metrics remain unresolved in the product documentation; do not invent them.

## Brand Commitments

Keep the Kien name, current brand assets, Ink Blue and Ochre identity on a clean
neutral black-and-white style (white and light-gray surfaces, near-black dark theme). The approved compact dashboard geometry is
recorded in DESIGN.md and docs/DESIGN_SYSTEM.md. The sidebar remains resizable,
phone navigation remains a sheet, theme selection stays above the account block
with its sliding highlight and original circular reveal, and workspace search
remains beside Open checklist. Voice is direct, factual and task oriented.

## Evidence on Hand

AGENTS.md, docs/PRD.md, docs/DESIGN_SYSTEM.md, docs/ARCHITECTURE.md,
docs/DATABASE.md, docs/SECURITY.md, docs/CODE_STYLE.md and docs/TESTING.md are the
implementation-grounded references. The canonical request catalog is
`data/checklist/aml_bd_v1.yaml`; brand marks live in `web/public/brand`.
Tests and seed data are synthetic. Do not fabricate client evidence, testimonials,
regulatory approval, automated audit conclusions or business performance claims.

## Product Principles

1. Make the user's next permitted task and current state clear.
2. Keep collection, human review and human approval distinct.
3. Preserve tenant and engagement boundaries on the server.
4. Prefer familiar, consistent controls over decorative novelty.
5. State uncertainty and unfinished decisions honestly.

## Accessibility & Inclusion

Preserve semantic labels, visible keyboard focus, focus-managed overlays,
reduced-motion behavior, browser zoom, readable contrast and narrow-screen use.
Automated checks support this work; they do not establish accessibility or
regulatory certification.
