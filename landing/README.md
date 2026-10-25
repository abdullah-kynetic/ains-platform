# Kien public site

Static landing page for [kiensolutions.com](https://kiensolutions.com/), published as its own Cloudflare Worker (`kien-solutions`). It is not the client portal in `web/`.

The page is HTML, CSS, a small SVG mark, and two self-hosted fonts. There is no build step.

## Deploy

Do this only when you mean to publish. It uploads the Worker. It does not attach `kiensolutions.com` or `www`, and it does not change those DNS records, because `wrangler.jsonc` has no routes.

From the repository root, with `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` in the environment (do not commit them):

```sh
cd landing
npx wrangler@4.151.3 deploy
```

Wrangler 4.151.3 matches the portal's `web` dependency. The first deploy also creates the `workers.dev` preview hostname because `workers_dev` is true. That hostname is not the custom domain.

After both custom domains below answer, you may set `"workers_dev": false` and deploy again if the preview URL should go away. Leave it true until the custom domains work, or the Worker has no public hostname.

## Domain setup

Use **Custom Domains**. This Worker is the site itself, so a route in front of another origin is the wrong attachment. The zone `kiensolutions.com` must already be on the same Cloudflare account.

1. Deploy the Worker once with the command above.
2. In the Cloudflare dashboard open **Workers & Pages → kien-solutions → Settings → Domains & Routes → Add → Custom Domain**.
3. Enter `kiensolutions.com` and confirm. Cloudflare creates the proxied apex DNS record and the certificate. Do not add a separate apex A or CNAME first. A hostname that already has a CNAME cannot take a Custom Domain until that CNAME is removed.
4. Add a second Custom Domain, `www.kiensolutions.com`. Cloudflare creates the proxied `www` record.

Both hostnames then serve this Worker. The page's canonical URL is `https://kiensolutions.com/`.

To send `www` to the apex, add a Redirect Rule on the zone (Rules → Redirect Rules):

- If hostname equals `www.kiensolutions.com`
- Then dynamic redirect to `https://kiensolutions.com${uri.path}`
- Status 301, preserve the query string

Turn on **SSL/TLS → Edge Certificates → Always Use HTTPS** for the zone.

Adding this to `wrangler.jsonc` makes the next `wrangler deploy` create those DNS records. Leave it out until you want that:

```jsonc
"routes": [
  { "pattern": "kiensolutions.com", "custom_domain": true },
  { "pattern": "www.kiensolutions.com", "custom_domain": true }
]
```

### Route alternative

Use routes only if this Worker should sit in front of an existing proxied origin. Custom Domains are the right choice for this site.

DNS, proxied (orange cloud), before the route will receive traffic:

- Apex: `AAAA` `@` → `100::`, or `A` `@` → `192.0.2.0` (placeholder addresses; Cloudflare intercepts proxied traffic)
- `www`: the same kind of proxied placeholder, or a proxied CNAME to `kiensolutions.com`

Then add routes on the Worker (zone `kiensolutions.com`):

- `kiensolutions.com/*`
- `www.kiensolutions.com/*`

`kiensolutions.com` without `/*` matches only the root path.

## Local preview

```sh
cd landing
npx wrangler@4.151.3 dev
```

The browser test serves `public/` directly and runs with the portal suite:

```sh
cd web
npm ci
npx playwright install chromium
npm run test:e2e
```
