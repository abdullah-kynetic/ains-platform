# Design System

Root [DESIGN.md](../DESIGN.md) records the incumbent Kien/shadcn visual system in
Impeccable's machine-readable and narrative format; [PRODUCT.md](../PRODUCT.md)
records confirmed product truth. `.impeccable/review.md` records the refinement
assessment. These preserve the historical context below. Shared heading/prose
roles now protect long tokens, balance headings and limit explanatory copy to
75ch without narrowing data tables. Reduced motion explicitly removes transitions
and animations while retaining visible final states; the original normal-motion
theme control is unchanged. Sidebar pointer ownership and blur cleanup keep
interrupted drags recoverable without changing widths, thresholds or persistence.

## Current visual system

Kien uses a clean neutral black-and-white SaaS style (calm, serious, premium for compliance buyers). [DESIGN.md](../DESIGN.md) holds the tokens, the Ink/Ochre/Status rules and the "Why" principles; this file records components, layout and accessibility. It replaces the earlier cream, ochre-tint, glass and gradient looks.

- **Brand attributes:** calm, precise, trustworthy. Responsive web on desktop and phone; tablet stays usable. Source of truth is `web/src/app/globals.css` and the shared components.
- **Surfaces:** white cards on a `#F7F7F8` canvas, thin `#E5E7EB` borders, 12px card radius, 32px controls, no gradients or glows. Dark mode uses a `#0A0A0A` canvas and `#111113` surfaces.
- **Ink `#33405C`** is used only for the logo mark, primary buttons, active navigation and focus rings. **Ochre `#B8924A`** is used only for deadline and needs-attention badges. Red, amber and green appear only as small soft-tinted status pills.
- **Sidebar:** grouped sections with small gray labels and count badges. Auditor: Workspace (Today, Clients, Notifications), Engagements (Engagements, Audit pipeline, Reports, Invoices), Firm (Firm settings, Audit Log, My account). Client: Engagement, Updates, Results (Responses requested, Report, Invoices). The theme switch stays above the account block, the collapsed rail is icon-only, and phones get a sheet. It is resizable and remembers its width.
- **Pages:** the auditor home is Today. Engagement workspaces use route tabs (`LinkTabs`). No nested cards: use dividers inside a card.
- **Components:** shadcn-style primitives in `web/src/components/ui` and Lucide icons only. `Field` associates its label with its control; scrollable tables are keyboard-focusable.
- **Statuses on new screens:** conclusions (Pass / Partial / Fail / Does not apply), finding status and severity, and sample results use the shared `Badge` variants.

## UI tokens

Values below are sourced from `web/src/app/globals.css` on main. Mix-based values are intentionally stated as formulas rather than guessed hex values.

| Token | Value | Usage |
| --- | --- | --- |
| `color.ink` | `#33405C` | Brand Ink Blue and light foreground |
| `color.ochre` | `#B8924A` | Brand Ochre accent |
| `color.background` (light) | `#F7F7F8` | Neutral canvas |
| `color.surface` (light) | `#FFFFFF` | Cards and controls |
| `color.sidebar` (light) | `#F7F7F8` | Sidebar |
| `color.ink-deep` | `#242D40` | Dark background base |
| `color.background` (dark) | `#0A0A0A` | Dark canvas |
| `color.foreground` (light) | `#0A0A0A` | Primary text (Ink is not the text color) |
| `color.danger` | `#DC2626` (text `#B91C1C`) | Error/status color; always paired with text |
| `font.sans` | `-apple-system`, `BlinkMacSystemFont`, `Inter`, `Segoe UI`, `Roboto`, `Helvetica Neue`, `Arial`, sans-serif | Main branch system stack; Inter is a fallback, not locally bundled on main |
| `font.mono` | `ui-monospace`, `SFMono-Regular`, `SF Mono`, `Menlo`, `Consolas`, monospace | Code and identifiers |
| `font.scale` | 12/14/16/18/20/24/28px with line heights 16/20/24/28/28/32/36px | Tailwind xs through 3xl tokens in main |
| `space.unit` | 4px | 8px base grid; actual scale 4, 8, 12, 16, 24, 32, 40, 48, 64px |
| `radius.control` | 8px | Inputs and buttons |
| `radius.card` | 12px | Cards |
| `shadow.card` | `0 1px 2px var(--color-shadow)` | Cards |
| `control.height` | 32px | Buttons, inputs, selects, summary, file inputs |


## Layout rules

- **Container widths, gutters, breakpoints:** Main CSS has no single fixed content max-width token. Desktop sidebar activates at Tailwind `lg` (1024px); mobile navigation is a focus-managed sheet below that. Sidebar default width 256px; persisted drag width clamped 200–360px; collapsed rail 48px in the layout preview. The exact snap/collapse threshold is implemented in `web/src/components/shell/nav.tsx` and should be preserved there.
- **Grid, spacing, alignment:** Use the existing 4px-derived spacing tokens; group related content with 8px multiples. Use hairline `--color-border` borders and existing soft shadows. Prefer compact tiles with the primary action at top right. The layout preview adds the navigation-only header described above.
- **Mobile behavior:** Sidebar is replaced with a sheet; preserve focus entry/return and keyboard close behavior. Ensure content and file controls fit narrow screens without horizontal overflow.
- **Shell:** Desktop sidebar can resize and collapse, remembers state, and shows icons only when collapsed. Theme control is directly above identity/firm/logout content. Client firm identity is a plain firm card; workspace switching and add-workspace are auditor-only.
- **Checklist:** Search is inline next to the “Open checklist” action where that combined view exists; checklist filtering remains local to the checklist screen.

## Components

Shared components live in `web/src/components/ui/`, with shell, checklist, auditor, and tenant-specific components in sibling folders. Reuse the existing Button, Input, Card, Dialog, Badge, Tabs, Table, LoadState, EmptyState, Skeleton, and Toaster.

- **Primary button:** Existing `button.tsx` variants; Ink/brand fill in light theme and accent tokens by theme. Keep concise verb-first labels. Preserve minimum control height and disabled semantics. Loading is explicit in flow-level components; do not imply success before API completion.
- **Form field:** Visible associated label, optional helper text, validation and error adjacent to the control; use native semantics and `aria-describedby`/live regions as appropriate. Preserve current password/upload constraints.
- **Card/tile:** Quiet surface, thin border and soft shadow; compact layout. Primary action at top right. Clickable behavior must be keyboard-accessible and visibly focused.
- **Dialog/sheet/navigation:** Modal semantics, focus containment/return, escape behavior, accessible names; mobile nav remains a sheet.
- **Theme switch:** Light/Dark/System with sliding selection highlight. When collapsed it becomes a vertical icons-only control. Circular reveal originates at pointer/keyboard activation; reduced-motion bypasses the reveal.
- **States for all controls:** Default has readable contrast and clear affordance. Hover is subtle and not the only feedback. Focus is visible for keyboard users. Disabled state cannot activate and remains legible. Loading announces progress and prevents duplicate submissions. Error includes text and recovery when possible. Success confirms the completed action. Avoid color-only communication.

## Accessibility

- Keyboard navigation and visible `:focus-visible` outline are global base rules; preserve native semantics, labels, and focus management. Current main outline color follows `--color-focus`; the owner’s Ochre keyboard-only focus rule is desired but not fully implemented as specified.
- Honor `prefers-reduced-motion: reduce` by removing/nearly eliminating animations and transitions; theme reveal and sidebar transitions must not obstruct interaction.
- Pair error/success/warning colors with text and labels. Do not claim contrast conformance without measuring the actual computed theme colors; automated browser accessibility tests are coverage, not certification.
- Provide semantic landmarks, accessible names, alt text where needed, adequate hit areas, and screen-reader status/error announcements.
- Browser e2e includes accessibility-tagged rules and phone dimensions; see [Testing](TESTING.md).

## Screen states

- **Client home/checklist/upload/questionnaire/progress:** populated, empty checklist/activity, loading skeleton/status, recoverable API error with retry, per-file upload validation/error/receipt. Journey F-01–F-04.
- **Auditor portfolio/engagement/tasks/audit log:** populated and no assigned work, loading, API failure with retry, empty search/filter result, readiness blockers. Journey F-05–F-07.
- **Sign-in/invitation/reset/MFA:** removed from the web app for the demo phase (`/sign-in` redirects to `/`). Restore their loading, error and recovery states with auth. Journey F-08–F-09.
- **Unknown firm/wrong portal:** explicit explanation and safe navigation/sign-out path; do not leak firm records. Journey F-01.
- **Synthetic demo:** clearly label demo interactions and synthetic data; never represent them as real authentication, storage, email, findings, or sign-off.

## Approval

Design owner: the product owner approved the neutral style on `design/preview-cleanup`. Source of truth: `web/src/app/globals.css`, the shared components and DESIGN.md.

## Invoice surfaces

The auditor-only register, draft form and detail reuse the existing shell, card, field,
button, badge and native dialog components. Status pills include text; fields have visible
labels. Add/remove lines and payment dialogs support keyboards and narrow screens.
Print media shows the invoice content with dark text on white and hides navigation,
actions and internal history. The existing global type scale and theme tokens remain
unchanged. Synthetic mode explicitly labels local metadata and absence of email/payments.


## Numbered checklist N/A

All 34 catalog requests remain visible with their original numbers; N/A sorts last.
Clients can directly set/undo N/A on their own engagement; its assigned auditor can
also set/undo it. Questionnaire no answers and the legacy representation endpoint
now set N/A directly. Existing pending claims remain readable and reviewable for
compatibility. N/A counts as done; collection still excludes the two restricted items
(32 ordinary requests). Restricted-content handling and upload prohibitions remain.
Undo restores `na_previous_state` (revision `a113_checklist_na`). The existing
`na_approved_by_id` stores the marking actor for both roles; the related user supplies
`naMarkedByRole`. Each toggle records actor ID and role in the immutable audit chain.
No schema migration is needed. This collection declaration is not an audit finding.
Auditor workspace links come from server-authorized assignments rather than a disabled
synthetic client-role switch. Unassigned auditors and other firms remain denied.


## Editable auditor reports

The existing report template, approved finding drafts, legacy DOCX/PDF generator and
hash-attestation sign-off remain in place. `/auditor/reports` adds persisted editing
per assigned engagement in `engagement_reports` (additive `a114_engagement_reports`).
Firm/period/scope and 34 request statuses are snapshotted server-side on create/save.
Approved findings prefill the narrative; auditors enter per-item report findings.
Restricted items allow metadata only. The native rich-text editor accepts text paste;
the server keeps only formatting tags with no attributes, scripts, URLs or embedded content.
Version checks and row locks prevent lost updates. Finalization requires explicit human
attestation, freezes content and records its SHA-256. Audited reopening permits edits;
prior final hashes remain in the immutable audit chain. Final status does not complete
the engagement, deliver a report, establish a clean opinion or create a cryptographic
signature. Clients receive 403 and have no report navigation; unassigned auditors get 404.
Print view uses the invoice-style browser print/save PDF flow. The idempotent
`python -m app.report_seed` seeds one existing explicitly synthetic demo engagement.


## First sign-in walkthrough

`GET/POST /auth/onboarding` reads/finishes only the authenticated user's preference.
Nullable `users.onboarding_state` and `onboarding_finished_at` are added by
`a115_user_onboarding`; null means pending. Completed/skipped states are terminal
through the public endpoint and audited once. Each role has a three-step skippable
modal using the existing dialog, focus handling, tokens and reduced-motion behavior.
The app has auditor/client roles and no distinct firm-admin role; the auditor flow
explains the workspace management auditors already have permission to use.
`python -m app.onboarding_seed --reset-demo` resets only the two exact existing
synthetic demo identities, preserves credentials and records demo reset events.
Demo walkthroughs stay finished after verification; reset only for an explicit demo run.
`UserView` includes nullable `onboarding_state` in sign-in, invitation acceptance and
`GET /auth/session`. Both roles open the tour only for null state, with no extra GET
required. Completing, skipping, Close and Escape save through the same idempotent
POST; the session updates only after a successful save. Failed saves stay visible
with a retryable error. Live mode never uses localStorage for onboarding state.
New users start null; existing pending users are not backfilled. No new migration
is needed beyond `a115`. Static browser mocks have no sign-in;
set `kien-synthetic-onboarding-enabled=1` to exercise their local walkthrough state.
