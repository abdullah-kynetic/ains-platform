import type { ErrorEvent, EventHint } from "@sentry/browser";

// Rebuild from a tiny allowlist: arbitrary strings may contain client documents,
// SAR content, emails or credentials, even in exception values or stack locals.
export function scrubEvent(event: ErrorEvent, hint: EventHint): ErrorEvent {
  delete hint.attachments;
  const frames = (event.exception?.values ?? []).flatMap((exception) =>
    (exception.stacktrace?.frames ?? []).map((frame) => ({
      ...(Number.isInteger(frame.lineno) ? { lineno: frame.lineno } : {}),
      ...(Number.isInteger(frame.colno) ? { colno: frame.colno } : {}),
    })),
  );
  return {
    type: undefined,
    level: "error",
    exception: { values: [{
      type: "ApplicationError",
      value: "Application error (details withheld)",
      stacktrace: { frames },
    }] },
  };
}
