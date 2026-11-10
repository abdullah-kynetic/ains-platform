# Multi-tenant portals

`kiensolutions.com` and `www.kiensolutions.com` are the landing page. Each licensed or
white-label firm uses `https://<slug>.kiensolutions.com` (for example
`kynetic.kiensolutions.com`). One Next.js deploy sits behind Cloudflare
`*.kiensolutions.com`. `api.kiensolutions.com` stays the single shared backend.

Synthetic data only. This change does not apply Terraform or touch AWS state.

## Slug

`firms.slug` already existed as a unique label. Migration `a118_firm_portal_slug` does
not add a second column. On PostgreSQL it lowercases stored values and adds
`ck_firms_portal_slug`: one DNS label, 1–63 characters, `[a-z0-9-]`, not starting or
ending with a hyphen, and not one of `www`, `api`, `app`, `admin`, `mail`, `status`.
The ORM rejects the same values. Fix any existing slug that fails the check before
`alembic upgrade head`. Migration `a119_firm_logo_url` adds a nullable `firms.logo_url`
used only by public branding.

## Which host a request belongs to

The API reads `Origin`, then `X-Forwarded-Host`, then `Host`.

Production (`PORTAL_BASE_DOMAIN=kiensolutions.com`):

- `https://<slug>.kiensolutions.com` is that firm. `api.<base>` is ignored when a firm origin is also present, which is how a browser call to `api.kiensolutions.com` is tied to the portal.
- The apex and `www` are the landing page. `www`, `api`, `app`, `admin`, `mail`, and `status` are reserved.
- `http://<slug>.localhost:3000` is not a firm, even when that slug exists.

Development (no base domain, and `SESSION_COOKIE_SECURE` left false):

- `http://<slug>.localhost` is that firm. The dev portal origin is `http://<slug>.localhost:3000`. The port is not part of the slug.
- Bare `localhost` and `testserver` do not turn binding on.
- A production base domain or `SESSION_COOKIE_SECURE=true` disables localhost firm hosts. Production sets both.

One firm label must match `firms.slug`. Two different firm labels conflict. A firm-bound user (client or white-label auditor) can use only their slug. A platform
auditor with no `firm_id` may open a resolved firm portal; engagement queries still
limit them to assignments. Sign-in on the wrong portal returns 403 and does not set a
cookie.

## Cookies: direct API calls, server-side binding

The portal keeps calling `NEXT_PUBLIC_API_URL` (`https://api.kiensolutions.com` in
production, `http://localhost:8000` in dev) with `credentials: "include"`. This
backend leaves that working.

`ains_session` is `HttpOnly`, `Path=/`, `SameSite=Lax`, `Secure` in production, and
has **no `Domain` attribute**. Do not set `Domain=.kiensolutions.com`.

That cookie does **not** isolate firms. The browser stores it for
`api.kiensolutions.com` only, and every firm portal sends that same cookie when it
calls the API. `kynetic.kiensolutions.com` and `api.kiensolutions.com` are different
origins and the same site (registrable domain `kiensolutions.com`):

- `SameSite=Lax` and `SameSite=Strict` both send the cookie on those same-site fetches.
- `SameSite=None` would also send it to unrelated sites. It is not used.
- `SameSite` does not distinguish one firm subdomain from another.

Isolation is the server check: the session user's `firm_id` must equal the firm for
the portal `Origin` (or `Host`, when that host is the firm). A user from firm A is
rejected on firm B's origin, and the sign-in response does not set a cookie. One
login still replaces the single API cookie, so two firms cannot stay signed in at
once. A missed check on any route would be a cross-tenant hole, and a page on a
sibling subdomain can submit state-changing API requests with the victim's cookie.
CORS only stops JavaScript from reading the response.

### If the frontend later proxies `/api`

Proxying `/api` on each portal host would make the cookie host-only for
`<slug>.kiensolutions.com` and would isolate firms in the browser as well as on the
server. The API would still bind the session to the portal firm. To switch, the
frontend would:

- set `NEXT_PUBLIC_API_URL=/api` (a same-origin path, not `https://api.kiensolutions.com`)
- keep `credentials: "include"`
- proxy `/api/:path*` to `https://api.kiensolutions.com/:path*` and set `Origin` (and `X-Forwarded-Host`) from the portal `Host` on every forwarded request, including GET
- forward `Cookie` and return `Set-Cookie` unchanged, still with no `Domain`

Do not do that until the portal stops calling the API host directly. The current
portal does not proxy.

## CORS

Credentialed responses never use `*` and never echo an arbitrary `Origin`.
An origin is allowed only when it is:

- an exact `CORS_ORIGINS` entry (local `http://localhost:3000`; production leaves this empty), or
- `https://<portal base>` or `https://www.<portal base>`, or
- `https://<slug>.<portal base>` where `<slug>` is a real `firms.slug`, or
- in development only, `http://<slug>.localhost` with the portal port (`http://<slug>.localhost:3000`).

`http://<slug>.localhost:3000` is refused when `PORTAL_BASE_DOMAIN` is set or
`SESSION_COOKIE_SECURE=true`, including when that origin is copied into
`CORS_ORIGINS`. Reserved labels and unknown slugs are not echoed.

The slug set is cached for 30 seconds and cleared when a firm row changes. A label
that merely looks like a subdomain is denied. Allowed methods are `GET`, `POST`,
`PUT`, `PATCH`, `DELETE`, and `OPTIONS`. Preflight rejects any other method or request header. Allowed request headers are `Authorization` and
`Content-Type` (`X-Forwarded-Host` is not allowed, so browser JavaScript cannot
attach it cross-origin).

## Public branding

`GET /tenant/branding` does not require a session. It resolves the firm from
`Origin` or `Host` and returns only:

```json
{"name": "Synthetic Alpha Securities", "logoUrl": "/brand/synthetic-alpha.svg"}
```

`logoUrl` is the firm's optional public logo (`https://` URL or a site path) or
`null`. Unknown slugs, reserved hosts, the landing page, and localhost firm hosts
in production return 404 `{"detail": "Unknown firm portal"}`. The body has no firm
id, slug, users, or engagements.

## Email links

`PORTAL_URL=https://{slug}.kiensolutions.com` is expanded with the firm's slug for
invitation, password reset, magic link, and report-ready mail. A URL without
`{slug}` (local `http://localhost:3000`) is used as written. Platform auditors have
no firm, so their links use the fixed auditor host. Report-ready mail goes only to active client
users of that firm and does not include findings or a report digest. Sign-off still
succeeds when email is not configured.

## Hosting boundary

One production Worker and one API are the current plan. Terraform and DNS changes
are outside this rebuild. Code lanes have no server access; Lane C configures the
single environment. No hosts or cloud resources are changed by this PR.

Required API configuration names: `SESSION_COOKIE_SECURE`, `CORS_ORIGINS`,
`PORTAL_BASE_DOMAIN`, `PORTAL_URL`, and `EMAIL_FROM`. Production uses secure cookies,
HTTPS portal origins, and no localhost entries. See [BUILD-PLAN.md](BUILD-PLAN.md).

## What the frontend keeps, and what a proxy would change

Keep the current calls. Production build:
`NEXT_PUBLIC_API_URL=https://api.kiensolutions.com`. Dev:
`NEXT_PUBLIC_API_URL=http://localhost:8000`, portal at
`http://<slug>.localhost:3000`, `PORTAL_BASE_DOMAIN` empty,
`SESSION_COOKIE_SECURE=false`. Keep `credentials: "include"`. Do not set a cookie
`Domain`. Read branding from `GET /tenant/branding` (`name`, `logoUrl` only).

That arrangement relies on server-side firm binding, not per-firm cookies. The
proxy alternative is in the cookie section above.

## Open pull requests

| PR | Overlap |
| --- | --- |
| [#36](https://github.com/abdullah-kynetic/ains-platform/pull/36) | Brand copy in `app/auth/email.py`, `app/config.py`, `app/main.py`, `.env.example`, `docs/deploy-aws.md`, and the auth tests. Keep the Kien Solutions wording and the `{slug}` links. |
| [#37](https://github.com/abdullah-kynetic/ains-platform/pull/37) | Production `NEXT_PUBLIC_API_URL=https://api.kiensolutions.com` matches the direct API calls kept here. CORS in that PR is a fixed list; this PR allows apex, `www`, known slugs, and dev localhost. `docs/deploy-aws.md` and `infra/aws/terraform.tfvars.example` will conflict. |
| [#39](https://github.com/abdullah-kynetic/ains-platform/pull/39) | `docs/deploy-aws.md` only. No schema or auth overlap. |
| [#40](https://github.com/abdullah-kynetic/ains-platform/pull/40) | Resend payloads, sign-off mail, `app/auth/email.py`, `app/api/auditor.py`, `app/config.py`, reset tests, and the auth docs. Keep that delivery behavior and point every link through `portal_url_for`. |
| [#44](https://github.com/abdullah-kynetic/ains-platform/pull/44) | Firm hosts and dev `<slug>.localhost`. Branding is still a mock `{name, logoUrl}` until it calls `GET /tenant/branding`. `docs/deploy-aws.md` and `web/` will conflict. This PR does not change the portal. |
