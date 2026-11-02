# Design system

The approved design is neutral black-and-white. Sources: [DESIGN.md](../../DESIGN.md), [component and accessibility guide](../DESIGN_SYSTEM.md), `web/src/app/globals.css`, shared UI primitives and PRODUCT.md.

| Role | Light | Dark |
| --- | --- | --- |
| Canvas / sidebar | `#F7F7F8` | `#0A0A0A` |
| Cards / controls | `#FFFFFF` | `#111113` |
| Main text | `#0A0A0A` | `#FAFAFA` |
| Muted text | `#636A77` | `#A1A1AA` |
| Borders | `#E5E7EB` | `#26262B` |

Ink `#33405C` is limited to the logo, primary buttons, active navigation and focus. Ochre `#B8924A` is for deadlines. Red/amber/green are small status pills with text. No cream, gradients or glass. Print layouts use white paper.

System sans typography, 4px spacing scale, 32px controls, 12px card radius. Reuse tokens rather than hardcoding new colors. Keep data tables wide while explanatory prose stays within 75ch.

Desktop sidebar defaults to 256px, resizes between 200–360px and collapses to a 48px icon rail. Phones use a focus-managed navigation sheet. Theme controls stay above identity; Light/Dark/System and sidebar state persist locally. Search sits beside page actions. Client identity is a static firm card.

Auditor navigation: Workspace, Engagements and Firm groups. Today is the auditor home; engagements use route tabs. Clients see Engagement, Updates and Results groups; Results contains Responses requested, Report and Invoices. Clients never see findings.

Keep keyboard focus, reduced motion, labels, contrast and phone overflow checks. UI changes require before/after desktop light, desktop dark and phone screenshots. Impeccable reference files are merged; they do not authorize a redesign. Separate design experiments require Abdullah's approval.
