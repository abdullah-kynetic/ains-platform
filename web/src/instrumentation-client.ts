import { scrubEvent } from "./lib/sentry";

// No SDK import, listeners or transport when the public build-time DSN is unset.
if (process.env.NEXT_PUBLIC_SENTRY_DSN?.trim()) {
  void import("@sentry/browser").then((Sentry) => {
    Sentry.init({
      dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
      sendDefaultPii: false,
      defaultIntegrations: false,
      integrations: [Sentry.globalHandlersIntegration()],
      tracesSampleRate: 0,
      maxBreadcrumbs: 0,
      sendClientReports: false,
      beforeSend: scrubEvent,
      beforeSendTransaction: () => null,
      tracePropagationTargets: [],
    });
  }).catch(() => { /* Monitoring availability must not affect the portal. */ });
}
