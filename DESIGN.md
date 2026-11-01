---
name: Kien
description: Independent AML testing workspace
colors:
  ink: "#33405C"
  ochre: "#B8924A"
  canvas: "#F7F7F8"
  card: "#FFFFFF"
  sidebar: "#F7F7F8"
  foreground: "#0A0A0A"
  muted: "#636A77"
  border: "#E5E7EB"
  success: "#16A34A"
  warning: "#D97706"
  danger: "#DC2626"
  dark-canvas: "#0A0A0A"
  dark-card: "#111113"
  dark-foreground: "#FAFAFA"
  dark-muted: "#A1A1AA"
  dark-border: "#26262B"
typography:
  headline:
    fontFamily: '-apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
    fontSize: "1.5rem"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "-0.03em"
  title:
    fontSize: "1rem"
    fontWeight: 500
    lineHeight: 1.375
  body:
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontSize: "0.75rem"
    fontWeight: 500
    lineHeight: 1.375
  metric:
    fontSize: "1.5rem"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.03em"
rounded:
  control: "8px"
  navigation: "6px"
  card: "12px"
  badge: "9999px"
spacing:
  s1: "4px"
  s2: "8px"
  s3: "12px"
  s4: "16px"
  s5: "24px"
  s6: "32px"
  s7: "40px"
  s8: "48px"
  s9: "64px"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "#FFFFFF"
    rounded: "{rounded.control}"
    height: "32px"
    padding: "0 10px"
  button-outline:
    backgroundColor: "{colors.card}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.control}"
    height: "32px"
    padding: "0 10px"
  navigation:
    rounded: "{rounded.navigation}"
    height: "32px"
    padding: "0 8px"
  input:
    backgroundColor: "{colors.card}"
    rounded: "{rounded.control}"
    height: "32px"
    padding: "4px 10px"
  card:
    backgroundColor: "{colors.card}"
    rounded: "{rounded.card}"
    padding: "20px"
  badge:
    rounded: "{rounded.badge}"
    height: "20px"
    padding: "2px 8px"
---

# Design System: Kien

## Overview

**Creative North Star: "The audit work is the hero"**

Kien is a clean, neutral black-and-white SaaS workspace in the family of Linear,
Stripe and Vercel: mostly white, restrained color, calm and serious. The design gets
out of the way so the audit work, not the chrome, is what people see. Brand stays
present but quiet.

This document records implemented visual rules; PRODUCT.md owns durable product
truth and docs/DESIGN_SYSTEM.md keeps the historical design context. The source
tokens in `web/src/app/globals.css` govern runtime themes. Never hardcode one-off
colors in components; add or change a token.

### Why this design (use these as principles for every decision)

- Compliance buyers (broker-dealers, auditors) trust calm, serious tools; loud color
  reads as a startup toy.
- Kien is priced premium; the best-in-class SaaS apps (Linear, Stripe, Vercel) are
  mostly white with restrained color.
- On a neutral page, color carries meaning: red, amber and green findings stand out
  instantly so auditors see what needs them.
- Fewer colors means fewer mistakes, less design drift and faster building.
- Kien will expand into many audit verticals (AML, SOC 2, financial audits); a neutral
  base fits all of them without redesign.
- Partner testing firms may add their own logo; a neutral base will not clash.
- Brand stays present but quiet: ink blue on the logo and primary actions, ochre for
  deadlines.

**Key Characteristics:**

- Neutral white and light-gray surfaces; near-black text; thin gray borders.
- Compact, task-oriented hierarchy with generous card padding.
- Familiar controls and server-authorized client/auditor workspaces.
- Responsive structure, visible focus and deliberate reduced motion.

## Colors

The base is neutral. Two brand hues have one narrow job each, and status colors
appear only where they mean something.

| Role | Light | Dark |
| --- | --- | --- |
| Page surfaces (cards, inputs, menus) | `#FFFFFF` | `#111113` |
| App canvas and sidebar | `#F7F7F8` | `#0A0A0A` |
| Primary text | `#0A0A0A` | `#FAFAFA` |
| Secondary text | `#636A77` (`#6B7280`, darkened one step so it holds AA on gray fills) | `#A1A1AA` |
| Borders | `#E5E7EB` | `#26262B` |
| Control borders (inputs, outline buttons) | `#868D99` (3:1 on white) | `#71717A` |

**The Ink Rule.** Ink Blue `#33405C` is used ONLY for the logo mark, primary buttons,
the active navigation item and focus rings. In dark mode the primary button stays
Ink with a lifted-ink border; focus rings and the active nav label use lighter
ink tints (`--color-focus`, `--color-nav-active`) so they stay legible on black.
Links and icons are neutral near-black, never Ink.

**The Ochre Rule.** Ochre `#B8924A` is used ONLY for deadline and "needs attention"
badges (`Badge variant="deadline"`). Its text color is a darkened ochre
(`--color-deadline-foreground`) so the pill passes AA.

**The Status Rule.** Red means fail or fix, amber means partial or waiting, green
means pass or improved. They appear as small soft-tinted pills (`Badge` success,
warning, danger) and change indicators, always with a word. Do not use them for
decoration or emphasis. Info and brand badges are neutral gray.

**No cream, no gradients, no glows.** Backgrounds are white or light gray only.
Shadows are soft and low. Progress bars are solid near-black.

Semantic aliases (`--background`, `--card`, `--primary`, `--sidebar-*`, `--ring`,
`--border`, `--input`) resolve from the same theme tokens. Legacy `text-muted`
means muted foreground text; `--muted` means an elevated surface. Paper output is
white with dark text regardless of the current screen theme.

## Typography

One native system sans stack carries headings, forms, labels, prose and data. The
existing system monospace stack is reserved for request identifiers and hashes.
No new font assets or display family are introduced.

Page headings use the headline role; card headings use the title role; compact
workflow text uses body; identifiers and supporting metadata use label sizing.
Metrics use tabular numerals and rise to (30px) when the stat container's content
width reaches (250px). Inputs use (16px) type on phones to preserve native zoom
behavior, and the compact body size on larger screens.

**The Reading Measure Rule.** Explanatory prose should remain within (75ch), use
natural paragraph rhythm and handle long tokens. Tables and compact data rows
retain their necessary widths. Balanced headings and pretty prose wrapping are
progressive enhancements, not manual line breaks or copy rewrites.

## Layout

The desktop sidebar begins at (256px), retains its saved (200–360px) drag range,
and collapses to a (48px) icon rail. Sidebar links and group labels are (32px)
high. The phone sheet is (288px) wide, capped by the viewport; the desktop sidebar
appears at (1024px). The existing native modal supplies focus containment/return.

Sidebar navigation is grouped under small gray section labels (for example
Workspace, Deliverables, Administration for auditors; Engagement, Updates for
clients). An item may carry a count badge computed from data its page already
loads; zero counts are hidden. The active item is a white pill with an Ink label
and icon. The thin breadcrumb header is (40px) on desktop and (64px) on phones.
Main content has no global maximum width:
horizontal padding is (16px) on phones and (24px) at the medium breakpoint; top
padding is (8px) and (16px), with (16px) bottom padding. Section/card gaps are
normally (16px), with (4–8px) relationships for labels and small control groups.
Data tables and the six-stage pipeline scroll inside their own regions.

**The Task Row Rule.** Workspace search stays beside the page action, including
Open checklist. Phone action wrapping must preserve that relationship. Keep
reading order aligned with DOM and keyboard order.

## Elevation & Depth

Cards are white with a (1px) `#E5E7EB` border and a soft one-pixel shadow. Floating
menus and overlays use the larger soft shadow tokens. Avoid heavy shadows, glass,
translucency and decorative depth.

## Shapes

Cards use the card radius; controls and framed tables use the control radius;
navigation links use the navigation radius. Badges alone use a pill silhouette.
The shapes establish hierarchy without decorative masks, custom illustrations or
new brand motifs.

## Components

### Buttons and fields

Primary actions are Ink with white text in both themes. Standard
controls are (32px) high; small buttons are (28px), large buttons (36px). Shared
fields have visible labels, invalid/disabled states and a theme-aware focus ring.
Multiline editors and file controls retain their appropriate natural size.
Compact controls are a deliberate owner requirement; do not inflate the desktop
layout solely to satisfy a generic touch-size preference.

### Cards, badges, tables and tabs

Cards are white, (12px) radius, with (20px) internal spacing, title/description
hierarchy and light divided footers where present. Do not nest bordered cards;
separate inside a card with dividers and spacing (tables inside cards use `Table
bare`). Stats are plain white cards. Badges are (20px) pill silhouettes. Tables
have light row dividers, a pale header row (40px), (12px) cell padding, and an icon
plus label in the first column; toolbars use compact gaps and pagination stays
below the table. Tabs are (32px) high with a (3px) inset and a quiet selected
surface.

### Auditor Today view

The auditor landing page leads with Today: "What needs your attention." It shows
four stat cards with change indicators, a "Needs you today" table (overdue and
due-today tasks, blocked engagements, work ready for sign-off), and upcoming
deadlines with ochre badges. It uses existing endpoints only (clients, pipeline,
tasks, activity). Change indicators are counts from the last 24 hours of
activity, never invented history. The assigned-engagement table and latest
activity follow.

### Sidebar, theme selection and overlays

**The Theme Placement Rule.** Light/Dark/System remains directly above the
account block. Preserve its sliding selection highlight, original circle reveal,
OS synchronization and persistence. Reduced motion skips the reveal and shows
the selected state immediately. Resizing, keyboard adjustment, collapse and the
phone pop-out menu stay available; interruption must release drag state.

Dialogs and sheets escape clipped containers, keep long headings readable and
leave dismissal reachable. Long firm names, task titles and report content may
wrap without widening the page. Do not truncate away the only route to task data.

## Do's and Don'ts

### Do:

- **Do** keep the page neutral; let status color mean something.
- **Do** keep typefaces, compact geometry and assets.
- **Do** use shared components for repeated controls across both roles.
- **Do** keep long content, empty/error/loading states, zoom and focus usable.
- **Do** preserve synthetic labels and the distinction between receipt and audit.

### Don't:

- **Don't** move theme controls into the header or separate search from its action.
- **Don't** replace sidebar resizing or the phone sheet with a parallel system.
- **Don't** change copy, business rules, authorization or backend processing for polish.
- **Don't** treat a detector preference as authority over an explicit owner decision.
- **Don't** use Ink or Ochre outside the roles above, or add gradients, glows or cream.
