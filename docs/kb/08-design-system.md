# Design system

Abdullah loves the current look. **Do not redesign it.** No generic "AI slop" visuals or filler copy. Source of truth: `web/src/app/globals.css`, shared components, `DESIGN.md`, `docs/DESIGN_SYSTEM.md`, `PRODUCT.md`.

## Palette
| Token | Value |
| --- | --- |
| Brand (light) — Ink Blue | `#33405C` (also light-mode text) |
| Accent — Ochre | `#B8924A` |
| Light background (cream) | `color-mix(in srgb, #B8924A 10%, white)` |
| Cards / controls (light) | `color-mix(in srgb, #B8924A 4%, white)` |
| Sidebar (light) | `color-mix(in srgb, #33405C 7%, white)` |
| Dark background | `#242D40` (deep ink); brand in dark mode is pale ochre |
| Error | `color-mix(in srgb, #B8924A 58%, black)` — always paired with text |
| Focus ring | Ink in light mode, pale Ochre in dark mode |
Print layouts stay white paper.

## Type
System stack: `-apple-system, BlinkMacSystemFont, Inter, Segoe UI, Roboto, Helvetica Neue, Arial`. Scale 12/14/16/18/20/24/28 px. Mono: `ui-monospace, SF Mono, Menlo, Consolas`. Prose capped at 75ch.

## Layout geometry (layout preview, #59 — not on `main` yet; from Kiranism shadcn starter)
- Inset: 16 px phone / 24 px desktop horizontal padding; 16 px section spacing.
- Sticky frosted header 56 px desktop / 64 px phone with breadcrumbs.
- Sidebar 256 px default, drag 200–360 px, saved; icon rail 48 px; phone = 288 px focus-managed sheet. Menu items 32 px.
- Cards: 12 px radius, subtle ring, 16 px padding, 16 px medium titles, tinted footers. Stat values 24 px (30 px when card ≥250 px).
- Controls 32 px (small 28, large 36). Badges 20 px pills. Tabs 32 px. Tables: 8 px radius, 40 px headers, 8 px cell padding.
- 4 px spacing unit (4, 8, 12, 16, 24, 32, 40, 48, 64).

## Owner rules
- Theme switch (Light/Dark/System, sliding highlight, circular reveal) sits directly **above** the user/firm/logout block. Saved in `ains-theme`.
- Collapsed sidebar = icons only; phone = pop-out sheet. Sidebar state saved in `kien-sidebar`.
- Clients see a plain firm card; firm switching / add-workspace is auditor-only.
- Workspace search sits **beside "Open checklist"**, not in the nav header.
- Compact tiles, primary action top-right.
- Keep reduced-motion, keyboard focus, labels, contrast, phone widths (375 px) working.
- Every UI change: before/after screenshots at desktop light, desktop dark and phone.

## Impeccable
Paul Bakaus's Impeccable design skill (pbakaus/impeccable, Apache 2.0) is vendored on `feat/shadcn-layout` (#59, unmerged — `PRODUCT.md`, `DESIGN.md` and `.impeccable/` are not on `main` yet). `PRODUCT.md` and `DESIGN.md` are in its machine-readable format; `.impeccable/review.md` holds the assessment (focused score moved 15/20 → 16/20; two detector findings intentionally left to preserve the palette and original animation). Use it for audits/polish, not to change brand.

## Design experiments
Go on their own address (e.g. design.kiensolutions.com, `kien-design-preview`, branch `feat/apple-polish` / PR #50). Never treated as approved until Abdullah says so.
