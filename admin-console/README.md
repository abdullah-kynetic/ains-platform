# Kien Admin preview

A self-contained, static preview of the Kien Solutions platform-owner admin console. Plain HTML, CSS, and vanilla JavaScript; no dependencies, build step, backend, network calls, analytics, or external assets.

All firms, people, metrics, and events are fictional. The sign-in and MFA screens are mock interactions, not access control. All static assets and synthetic data are public. Never enter real credentials or client information.

## Run locally

From this directory, serve the public folder with any static server, for example:

```sh
python3 -m http.server 8080 --directory public
```

Open `http://localhost:8080`. Hash routing supports direct links such as `/#firms/harbor`.

## Sign in

1. Enter any non-empty email and demo password. The email hint is `admin@kiensolutions.com`; use a made-up password.
2. Enter MFA code `123456`.
3. Explore Overview, Firms, Users, Audit log, and the read-only Settings view. Click a firm to see its users and usage.
4. Use **Sign out** to clear the demo session.

The demo session uses `sessionStorage` and survives reloads in the current tab. The theme follows your system preference until you toggle it; the explicit preference is saved in `localStorage`. If browser storage is unavailable, the preview still works without persistence. No email, password, or MFA code is stored.

Firm actions only update in-memory preview state and display “Demo only, nothing was changed”. No external resource changes. Reload to restore fictional firm data. The audit log is a fixed mock history.

## Deploy to Cloudflare

With Node.js/npm installed and Cloudflare Wrangler authenticated, run from `admin-console/`:

```sh
npx wrangler deploy
```

Wrangler may prompt for Cloudflare authentication if needed. The configuration deploys `public/` as static assets to the `kien-admin-demo` Workers service with a `workers.dev` URL. There is no Worker entry-point script or server logic. SPA fallback is enabled. Deployment requires a network connection; the deployed preview itself makes no network calls beyond loading its own static files.

The deployed URL is printed by Wrangler. Open it and follow the mock sign-in steps above.
