# Design System

## Design direction

- **Brand attributes:** Calm, precise, trustworthy.
- **Supported devices:** Responsive web on desktop and phone; tablet layouts should remain usable.
- **References:** Current source of truth is `web/src/app/globals.css` and shared components. `design.kiensolutions.com` on `origin/feat/apple-polish` is an unapproved design exploration; it is not the production reference.

### Main vs. design branch

Verified against `origin/main` and `origin/feat/apple-polish` at documentation time. Main already contains Ink/Ochre tokens, cream light surfaces, dark mode, reduced-motion overrides, focus-visible outlines, circular theme-reveal, a Light/Dark/System control, draggable/resizable and collapsible desktop sidebar with saved width/state, mobile navigation sheet, and active navigation styling. The theme choice persists in `ains-theme`; sidebar width/collapse in `kien-sidebar`. The branch adds locally served Inter variable font, an expanded type/token system and additional surface/card motion/polish. Those branch-only visual refinements are not approved for production. The branch must not be treated as an approval to replace the current look.

Owner-required design rules to preserve: sidebar theme switch sits directly above the user/firm/logout block; collapsed sidebar is icon-only; sidebar becomes a pop-out sheet on phones; keep a firm card for clients and firm switching/add-workspace auditor-only. Search belongs inline beside “Open checklist” with no global top bar. A keyboard-only Ochre focus ring is an intended design rule; current main has a generic focus-visible outline tied to `--color-focus` (Ink in light mode), so the explicit keyboard-only/Ochre behavior is unresolved against live code.

## UI tokens

Values below are sourced from `web/src/app/globals.css` on main. Mix-based values are intentionally stated as formulas rather than guessed hex values.

| Token | Value | Usage |
| --- | --- | --- |
| `color.ink` | `#33405C` | Brand Ink Blue and light foreground |
| `color.ochre` | `#B8924A` | Brand Ochre accent |
| `color.background` (light) | `color-mix(in srgb, #B8924A 10%, white)` | Warm cream main canvas, not pure white |
| `color.surface` (light) | `color-mix(in srgb, #B8924A 4%, white)` | Cards and controls |
| `color.sidebar` (light) | `color-mix(in srgb, #33405C 7%, white)` | Sidebar |
| `color.ink-deep` | `#242D40` | Dark background base |
| `color.background` (dark) | `#242D40` | Dark canvas |
| `color.foreground` (light) | `#33405C` | Primary text |
| `color.error` | `color-mix(in srgb, #B8924A 58%, black)` | Error/status color; pair with text/label |
| `font.sans` | `-apple-system`, `BlinkMacSystemFont`, `Inter`, `Segoe UI`, `Roboto`, `Helvetica Neue`, `Arial`, sans-serif | Main branch system stack; Inter is a fallback, not locally bundled on main |
| `font.mono` | `ui-monospace`, `SFMono-Regular`, `SF Mono`, `Menlo`, `Consolas`, monospace | Code and identifiers |
| `font.scale` | 12/14/16/18/20/24/28px with line heights 16/20/24/28/28/32/36px | Tailwind xs through 3xl tokens in main |
| `space.unit` | 4px | 8px base grid; actual scale 4, 8, 12, 16, 24, 32, 40, 48, 64px |
| `radius.control` | 8px | Inputs and buttons |
| `radius.card` | 10px | Cards |
| `shadow.card` | `0 1px 2px var(--color-shadow)` | Cards |
| `control.height` | 44px | Buttons, inputs, selects, summary, file inputs |

The requested Apple-style scale (28/22/17/15/13/11px) is not the token scale currently in main. `origin/feat/apple-polish` contains matching values: `--text-3xl` 28px, `--text-xl` and `--text-2xl` 22px, `--text-base` and `--text-lg` 17px, `--text-sm` 15px, `--text-xs` 13px, and `--text-label` 11px. Main instead has 28/24/20/18/16/14/12px for 3xl/2xl/xl/lg/base/sm/xs. The branch also ships an Inter variable font file and additional surface/card polish. Those changes are unapproved and not live on main; retain as documented design direction pending design-owner approval.

## Layout rules

- **Container widths, gutters, breakpoints:** Main CSS has no single fixed content max-width token. Desktop sidebar activates at Tailwind `lg` (1024px); mobile navigation is a focus-managed sheet below that. Sidebar default width 256px; persisted drag width clamped 200–360px; collapsed rail 76px. The exact snap/collapse threshold is implemented in `web/src/components/shell/nav.tsx` and should be preserved there.
- **Grid, spacing, alignment:** Use the existing 4px-derived spacing tokens; group related content with 8px multiples. Use hairline `--color-border` borders and existing soft shadows. Prefer compact tiles with the primary action at top right. Avoid adding a global top bar.
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
- **Sign-in/invitation/reset/MFA:** credentials, conditional MFA step, invalid/expired token, submitting, success, and recovery guidance. Journey F-08–F-09.
- **Unknown firm/wrong portal:** explicit explanation and safe navigation/sign-out path; do not leak firm records. Journey F-01.
- **Synthetic demo:** clearly label demo interactions and synthetic data; never represent them as real authentication, storage, email, findings, or sign-off.

## Approval

Design owner: Unresolved. Source of truth: current main CSS/components. `design.kiensolutions.com` on `origin/feat/apple-polish` remains an unapproved design branch reference.
