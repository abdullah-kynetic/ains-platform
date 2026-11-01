# Kien: design brief for mockups

Give this file to Claude Design along with 3 to 5 screenshots from https://preview.kiensolutions.com (no sign-in; use the workspace switcher at the top of the sidebar to flip between auditor and client).

## What Kien is
Kien, by Kien Solutions, is workflow software for independent AML testing of broker-dealers under FINRA Rule 3310. Auditors (a partner named Quentin signs every report) collect evidence from client firms, test 34 requests, record workpapers, samples and findings, build a report, and send it through second review and partner sign-off. Clients upload documents, answer a questionnaire, respond to auditor requests and download signed reports. Audience: compliance buyers. Tone: calm, serious, premium, trustworthy. All data in the product is synthetic.

## Current look (keep unless a mockup is better)
- Clean neutral black-and-white SaaS style, like Regline UI. White cards on a very light gray canvas, thin gray borders, near-black text, no gradients, glows, glass or shadows beyond a hairline.
- **Colour tokens, light:** canvas `#F7F7F8`, surface `#FFFFFF`, text `#0A0A0A`, muted text `#636A77`, border `#E5E7EB`, strong border `#868D99`.
- **Dark:** canvas `#0A0A0A`, surface `#111113`, text `#FAFAFA`, muted `#A1A1AA`, border `#26262B`.
- **Ink blue `#33405C`:** only for the logo mark, primary buttons, the active nav item and focus rings.
- **Ochre `#B8924A`:** only for deadlines and needs-attention badges.
- **Red, amber, green:** only as small soft-tinted status pills (Pass green, Partial amber, Fail red, Does not apply neutral gray).
- **Shape:** 12px card radius, 8px control radius, 32px control height, 4px spacing unit.
- **Type:** system sans stack (SF / Inter), sizes 12/14/16/18/20/24/28px, tabular figures for numbers.
- **Components and icons:** shadcn-style components and Lucide icons only.
- **Rules:** no cards inside cards (use dividers); WCAG AA contrast in light and dark; responsive down to a 390px phone; Light, Dark and System themes.

## Layout
- Left sidebar, resizable and collapsible to an icon rail, with small gray group labels and count badges. Theme switch sits above the account block. Phones use a slide-over sheet.
- **Auditor groups:** Workspace (Today, Clients, Notifications), Engagements (Engagements, Audit pipeline, Reports, Invoices), Firm (Firm settings, Audit Log, My account).
- **Client groups:** Engagement (Overview, Upload, Checklist, Questionnaire), Updates (Messages, Progress), Results (Responses requested, Report, Invoices).
- Page header: title, one-line description, primary action at top right, search (Cmd-K) beside it.

## Screens to mock up (pick one or two per request)
**Auditor**
1. Today dashboard: next deadline, needs-you-today, requests reviewed, "still to review" bar, needs-you-today table, upcoming deadlines.
2. Clients list and client profile (firm type, contacts, engagement history).
3. Engagement workspace with tabs: Overview, Requests, Documents, Checklist (34 items with Pass / Partial / Fail / Does not apply, N/A sorted last), Workpapers, Samples, Findings, Report, Independence, Sign-off, Activity.
4. Findings (condition, cause, effect, recommendation, severity, citations), report builder with fingerprint, sign-off steps.
5. Firm settings: team and roles, branding, checklist rubric, request-list templates.
6. Notifications centre and Cmd-K search.

**Client**
7. Overview and progress, upload and checklist, Responses requested (title, the auditor's request text, a reply box), signed report, invoices.

## Product rules the design must respect
- Clients never see audit findings, severity, cause or effect; they only see the auditor's request text on "Responses requested".
- Document feedback to clients is about the document only (unreadable, wrong period, missing pages).
- A report is signed only by an explicit partner action; show the report fingerprint (SHA-256) at sign-off.
- Mark synthetic or preview data with a subtle one-line note.

## What I want back
Three variants of the screen I name (one denser, one with more whitespace, one with a different header or table layout), each in light and dark, using only the tokens above unless you propose a change and say why. Keep the real navigation and labels. Tell me what you changed and why, so I can ask Claude Code to apply the one I choose.
