import { expect, test } from "@playwright/test";
import { scrubEvent } from "../src/lib/sentry";

test("telemetry drops arbitrary client content", () => {
  const synthetic = "synthetic@example.invalid synthetic-document-text";
  const hint = { attachments: [{ filename: synthetic, data: synthetic }] };
  const clean = scrubEvent({
    type: undefined,
    message: synthetic,
    request: { data: synthetic, cookies: { session: synthetic }, headers: { Authorization: synthetic } },
    user: { email: synthetic },
    extra: { document: synthetic, sar: synthetic },
    breadcrumbs: [{ message: synthetic }],
    exception: { values: [{ type: synthetic, value: synthetic, stacktrace: {
      frames: [{ filename: synthetic, vars: { contents: synthetic }, lineno: 42 }],
    } }] },
  }, hint);
  expect(JSON.stringify(clean)).not.toContain(synthetic);
  expect(Object.keys(clean).sort()).toEqual(["exception", "level", "type"]);
  expect(clean.exception?.values?.[0].stacktrace?.frames).toEqual([{ lineno: 42 }]);
  expect(hint).not.toHaveProperty("attachments");
});

test("portal makes no Sentry requests without a DSN", async ({ page }) => {
  const requests: string[] = [];
  page.on("request", (request) => {
    if (/sentry|\/envelope\//i.test(request.url())) requests.push(request.url());
  });
  await page.goto("/sign-in");
  await expect(page.locator("body")).toBeVisible();
  expect(requests).toEqual([]);
});
