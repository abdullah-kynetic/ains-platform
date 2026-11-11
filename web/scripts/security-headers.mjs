/**
 * Security headers for the web app (next.config.ts). One place, so a test can read them.
 *
 * CSP notes: Next.js emits inline bootstrap scripts, so script-src needs 'unsafe-inline' until a
 * nonce proxy is added (open item). Everything else is locked down: no plugins, no framing, no
 * base-tag or form-target tricks, and connections only to this site and the configured API (and the
 * public Sentry host when a DSN is set). Development adds 'unsafe-eval' and websockets for hot reload.
 */

/** The API origin(s) the browser may call. `{portal}` (local demo) becomes a leading wildcard host. */
export function apiConnectSources(apiUrl) {
  const raw = (apiUrl ?? "").trim();
  if (!raw) return [];
  try {
    const url = new URL(raw.replace("{portal}", "portal-placeholder"));
    const host = url.host.replace("portal-placeholder", "*.localhost");
    return [`${url.protocol}//${host}`];
  } catch {
    return [];
  }
}

export function contentSecurityPolicy(env, development = false) {
  // Same fallback as src/lib/api.ts: an unset API URL means the local API in dev, the real one otherwise.
  const apiUrl =
    env.NEXT_PUBLIC_API_URL?.trim() ||
    (development ? "http://localhost:8000" : "https://api.kiensolutions.com");
  const connect = ["'self'", ...apiConnectSources(apiUrl)];
  const dsn = env.NEXT_PUBLIC_SENTRY_DSN?.trim();
  if (dsn) {
    try {
      connect.push(new URL(dsn).origin);
    } catch {
      /* an unusable DSN adds nothing */
    }
  }
  if (development) connect.push("ws:", "http://127.0.0.1:*");
  const directives = {
    "default-src": ["'self'"],
    "script-src": ["'self'", "'unsafe-inline'", ...(development ? ["'unsafe-eval'"] : [])],
    "style-src": ["'self'", "'unsafe-inline'"],
    "img-src": ["'self'", "data:", "blob:"],
    "font-src": ["'self'", "data:"],
    "connect-src": connect,
    "frame-src": ["'none'"],
    "frame-ancestors": ["'none'"],
    "object-src": ["'none'"],
    "base-uri": ["'self'"],
    "form-action": ["'self'"],
  };
  return Object.entries(directives)
    .map(([name, values]) => `${name} ${values.join(" ")}`)
    .join("; ");
}

export function securityHeaders(env, development = false) {
  return [
    { key: "Content-Security-Policy", value: contentSecurityPolicy(env, development) },
    { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" },
    { key: "X-Frame-Options", value: "DENY" },
    { key: "X-Content-Type-Options", value: "nosniff" },
    { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
    { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=()" },
    { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  ];
}
