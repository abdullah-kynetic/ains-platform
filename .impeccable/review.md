# Impeccable review: existing Kien portal

Scope: `web/src`, client and auditor portal routes plus authentication/overlays.
Surface mode: **Operate**, explicitly specified by the owner. This is refinement
of the shipped Kien/shadcn system, not replacement of its visual world.

## Baseline and evidence

Impeccable skill 4.8.0 and detector engine 0.1.18 installed with the requested
project-scoped non-interactive command. `context` ran once before initialization;
its root scan missed the nested `web/` implementation, so source and existing
rendered evidence, rather than that absence heuristic, established the incumbent
system. PRODUCT.md records confirmed docs/owner truth without an interview, per
the owner's explicit no-questions instruction. DESIGN.md records source tokens,
geometry and state behavior; the extensions-only sidecar is design.json.

Two independent read-only assessments followed the layout/typeset references,
without detector anchoring. Evidence: existing client light/phone, auditor dark,
checklist phone, invoice and report-editor captures; shared CSS/components.
Mechanical source/type/layout scans followed the assessments.

## Layout and typeset assessments

- Reading order: firm/period and primary action, then client tasks/status/details;
  auditor portfolio summaries, then assigned records. DOM and phone order agree.
- Grouping: task tiles, status metrics, review details and timeline represent
  different work. Keep their compact 16px section / 4–8px internal rhythm.
- Density and structure: familiar forms, native overlays and a single sidebar
  serve repeat work. Table/pipeline scrolling is local to its own region.
- Adaptation: sidebar/sheet, responsive grids and wrapping action rows are sound.
  Unbroken firm titles were not: a 1440px viewport widened to 5875px; 768px and
  390px viewports widened beyond 5600px. See external stress JSON/screenshots.
- Type authority: retain the native system sans, fixed rem ramp, 24px page titles,
  16px card titles, compact 14px body, 12px metadata and tabular metrics. System
  font delivery introduces no font download or swap. Do not introduce a face.
- Reading measure: explanations need a 75ch ceiling and progressive pretty wrap;
  tables/data widths and established type sizes remain intact.
- Extremes: safeguard long headings, report prose, dismissal controls and pointer
  ownership. Existing empty/error/loading/permission handling remains in place.

## Technical audit

Implementation-integrity verdict: **pass with specific hardening work**. This is
an established task UI with meaningful status language and consistent primitives.
A detector preference is not evidence that an owner-approved style is a defect.

| Dimension | Before | After verification | Evidence / limit |
| --- | --- | --- | --- |
| Accessibility | 3/4 | 3/4 | Semantic labels/focus/modal behavior; existing axe checks; no formal conformance claim. |
| Performance | 3/4 | 3/4 | System fonts and no new runtime dependencies; no new profiling claim. |
| Theming | 3/4 | 3/4 | Palette/token preservation and light/dark/System browser coverage. |
| Responsive design | 3/4 | 3/4 | Long-name overflow fixed; automated viewport/touch coverage; no physical-device certification. |
| Implementation integrity | 3/4 | 4/4 | Shared prose/heading roles, documented authority, targeted gesture recovery and regression checks. |
| Total | 15/20 | 16/20 | Good; a scoped assessment, not certification. |

No P0 issues. P2 fixes (layout/typeset/harden), then whole-path polish:

1. **Unbroken firm/task/request headings can widen the page.** Use an existing
   heading role with emergency wrap and balanced text. Confirm desktop/tablet/
   phone and a 200%-equivalent CSS viewport. No name/copy truncation or editing.
2. **Explanatory prose has inconsistent measure.** Add shared prose measure,
   pretty wrap and explicit report-content wrapping. Preserve data-table widths,
   control sizes and all report text/sanitization. Editable report text already
   wrapped in the baseline browser; its new rule is defensive consistency.
3. **Drag ownership can be replaced by a second pointer; blur lacks cleanup.**
   Reject a second owner, ignore unrelated cancellation, and safely release capture
   on blur. Preserve width range, collapse threshold, keyboard and persistence.
   Test with Chromium CDP touch plus an explicit blur/cancel event and a subsequent
   real Playwright mouse drag; physical multitouch/window switching remains untested.

Additional polish: keep modal dismissal from shrinking beside long headings;
replace the 0.01ms reduced-motion duration hack with explicit animation/transition
none. All underlying selected/final states remain visible and the normal-motion
circle reveal and original switch easing remain byte-for-byte unchanged.

## Detector findings and owner exceptions

- `bounce-easing`: source scan flags the existing sidebar theme indicator's
  `cubic-bezier(0.22, 1.3, 0.36, 1)`. The owner explicitly requires its original
  animation. Retain the finding and value; no rule suppression added.
- `cream-palette`: URL scan flags the explicit 10% Ochre light background. Keep
  the requested palette and report the finding; do not recolor to game the count.

The URL detector sees unauthenticated public content and cannot establish the
quality of protected routes. Supplement with authenticated preview screenshots,
axe checks and the complete local synthetic workflow suite. Raw detector counts
are retained externally under /workspace/kien-compare/shadcn.

## Verification and remaining limits

The delivery report records exact final commands, counts, deployed version and
artifact paths. No backend source, API clients, permissions, model processing,
dependencies or copy changes are part of this pass. No new live-mode CSP or
imagery workflow is needed for this existing app refinement. The project-local
Codex hook and portable launcher are tracked; downloaded platform binaries and
runtime/cache files are local. Keep the two owner-approved findings visible.
