---
name: Kien
description: Independent AML testing workspace
colors:
  ink: "#33405C"
  ochre: "#B8924A"
  background: "color-mix(in srgb, #B8924A 10%, white)"
  card: "color-mix(in srgb, #B8924A 4%, white)"
  sidebar: "color-mix(in srgb, #33405C 7%, white)"
  dark-background: "#242D40"
  dark-card: "color-mix(in srgb, #242D40 93%, white)"
  dark-brand: "color-mix(in srgb, #B8924A 32%, white)"
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
    rounded: "{rounded.control}"
    height: "32px"
    padding: "0 10px"
  button-outline:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
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
    padding: "16px"
  badge:
    rounded: "{rounded.badge}"
    height: "20px"
    padding: "2px 8px"
---

# Design System: Kien

## Overview

**Creative North Star: "Precise audit workspace"**

The incumbent Kien system combines Ink Blue, Ochre and warm light surfaces with
the compact geometry of the Kiranism shadcn dashboard starter. Refinement keeps
that identity. Familiar navigation, quiet state treatments and stable information
density support repeated client and auditor work.

Brand expression comes from consistent type, spacing and controls rather than new
imagery or decoration. This document records implemented visual rules; PRODUCT.md
owns durable product truth and docs/DESIGN_SYSTEM.md keeps the historical design
context. The source tokens in `web/src/app/globals.css` govern runtime themes.

**Key Characteristics:**

- Compact, task-oriented hierarchy with restrained color.
- Familiar controls and server-authorized client/auditor workspaces.
- Warm light surfaces and deep ink dark surfaces.
- Responsive structure, visible focus and deliberate reduced motion.

## Colors

Primary Ink serves light-theme brand text and primary actions. Ochre supplies the
accent vocabulary and the pale dark-theme brand. Neutral surfaces are mixes of
these two established source hues, not a separate gray palette.

**The Existing Palette Rule.** Preserve the frontmatter's source hues and mixes.
Focus uses Ink in light mode and the existing pale Ochre focus token in dark mode.
Status colors remain existing ink/ochre shades and always accompany text.

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

The frosted navigation header is (56px) on desktop and (64px) on phones, with the
existing tablet header adaptation. Main content has no global maximum width:
horizontal padding is (16px) on phones and (24px) at the medium breakpoint; top
padding is (8px) and (16px), with (16px) bottom padding. Section/card gaps are
normally (16px), with (4–8px) relationships for labels and small control groups.
Data tables and the six-stage pipeline scroll inside their own regions.

**The Task Row Rule.** Workspace search stays beside the page action, including
Open checklist. Phone action wrapping must preserve that relationship. Keep
reading order aligned with DOM and keyboard order.

## Elevation & Depth

Cards use a subtle (1px) foreground ring. Low shadows support metrics and controls;
floating menus and overlays use the existing larger shadow tokens. The sticky
header's frosting distinguishes navigation from scrolling content. Avoid adding
heavy shadows or glass decoration to ordinary cards.

## Shapes

Cards use the card radius; controls and framed tables use the control radius;
navigation links use the navigation radius. Badges alone use a pill silhouette.
The shapes establish hierarchy without decorative masks, custom illustrations or
new brand motifs.

## Components

### Buttons and fields

Primary actions retain existing Ink/light and Ochre/dark behavior. Standard
controls are (32px) high; small buttons are (28px), large buttons (36px). Shared
fields have visible labels, invalid/disabled states and a theme-aware focus ring.
Multiline editors and file controls retain their appropriate natural size.
Compact controls are a deliberate owner requirement; do not inflate the desktop
layout solely to satisfy a generic touch-size preference.

### Cards, badges, tables and tabs

Cards have (16px) internal spacing, title/description hierarchy and tinted divided
footers where present. Stats use a restrained light-theme primary tint and solid
dark-theme cards. Badges are (20px) high. Table headers are (40px), cells use (8px)
padding, toolbars use compact gaps, and pagination stays below the table. Tabs
are (32px) high with a (3px) inset and a quiet selected surface.

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

- **Do** preserve the incumbent palette, typefaces, compact geometry and assets.
- **Do** use shared components for repeated controls across both roles.
- **Do** keep long content, empty/error/loading states, zoom and focus usable.
- **Do** preserve synthetic labels and the distinction between receipt and audit.

### Don't:

- **Don't** move theme controls into the header or separate search from its action.
- **Don't** replace sidebar resizing or the phone sheet with a parallel system.
- **Don't** change copy, business rules, authorization or backend processing for polish.
- **Don't** treat a detector preference as authority over an explicit owner decision.
