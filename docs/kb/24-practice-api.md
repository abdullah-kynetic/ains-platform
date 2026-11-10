# Practice routes (L2-6a)

Contract for Lane 1. Source: `app/api/firm.py`, tests `tests/test_firm_routes.py`,
`tests/test_practice_migration.py`. Shapes match `web/src/lib/api/types.ts` and `firm.ts`.

The **practice** is the auditing firm (Quentin's team). It is not a client `Firm`. Every route
derives the practice from the signed-in auditor (`users.practice_id`); no route takes a practice
id. Clients and auditors without a practice get 403. Member and template ids resolve inside the
caller's practice only, so another practice's ids return 404.

| Route | Who | Notes |
| --- | --- | --- |
| `GET /auditor/firm/team` | any team member | `TeamMember[]`; status is `invited` until the person signs in |
| `POST /auditor/firm/team` `{email, role}` | partner, admin | 201, returns the list; 409 if the email has an account |
| `PATCH /auditor/firm/team/{member_id}` `{role}` | partner, admin | only a partner can grant, change or remove `partner`; 409 for the last partner |
| `DELETE /auditor/firm/team/{member_id}` | partner, admin | 409 for the last partner, yourself, or a member with assigned engagements; sessions revoked |
| `GET/PUT /auditor/firm/branding` | read: any; write: partner, admin | `{name, logoDataUrl, tagline}` |
| `GET /auditor/firm/rubric` | any | all 34 requests; `criteria` empty and `enabled` true until set |
| `PUT /auditor/firm/rubric/{request_id}` `{criteria, enabled}` | partner only | other fields in the body are ignored |
| `GET /auditor/firm/request-templates` | any | built-in `tpl-all` first |
| `POST /auditor/firm/request-templates` | partner, admin | 201, returns the list |
| `PUT/DELETE /auditor/firm/request-templates/{id}` | partner, admin | `tpl-all` returns 409 |

Every write is in the audit chain with no client firm (`firm_id` null, `practice_id` in details).

## Decisions to review (Abdullah / Quentin)

- **Invites do not send email and the invitee cannot sign in yet.** The row is created inactive
  (status `invited`) so no one can sign in until a team accept-and-MFA flow exists. That flow is not
  built.
- **Logo:** `logoDataUrl` carries an `https://` URL or site path only; data URLs are rejected (422).
  The file upload to object storage comes with L2-7.
- **No invented templates or criteria.** The mock's three extra templates (introducing, retail,
  clearing) drop requests by guess, so they are not seeded. Partners create their own. Rubric
  criteria stay empty until a partner writes them.
- **Migration** puts every existing auditor into one practice named "Audit practice" and makes the
  earliest-created auditor its partner so someone can invite the rest. Rename it under branding.
- **Removing a member with assigned engagements is blocked** (409) rather than orphaning them. There
  is no reassign route yet.
