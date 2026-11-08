import { expect, test, type Page, type Route } from "@playwright/test";

async function enableLiveApi(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem("ains-e2e-live-api", "1");
  });
}

function fulfillJson(route: Route, status: number, body: unknown) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

async function brandingRoute(page: Page, status: number, body: unknown) {
  const seen: string[] = [];
  await page.route("**/tenant/branding", async (route) => {
    seen.push(route.request().url());
    expect(route.request().method()).toBe("GET");
    await fulfillJson(route, status, body);
  });
  return seen;
}

function expectDirectApiBranding(page: Page, seen: string[]) {
  expect(seen.length).toBeGreaterThan(0);
  const url = new URL(seen[0]);
  expect(url.pathname).toBe("/tenant/branding");
  expect(url.host).not.toBe(new URL(page.url()).host);
}

test("branding 200 applies the firm name and logo", async ({ page }) => {
  await enableLiveApi(page);
  const branding = await brandingRoute(page, 200, {
    name: "Synthetic Alpha Securities",
    logoUrl: "https://cdn.example/synthetic-alpha.svg",
  });
  await page.route("**/auth/session", (route) =>
    fulfillJson(route, 401, { detail: "Sign-in required" }),
  );
  await page.goto("/sign-in");
  await expect(
    page.getByText("Synthetic Alpha Securities", { exact: true }).first(),
  ).toBeVisible();
  await expect(
    page.locator('img[src="https://cdn.example/synthetic-alpha.svg"]').first(),
  ).toBeVisible();
  expectDirectApiBranding(page, branding);
});

test("branding 200 with a null logo keeps the Kien mark", async ({ page }) => {
  await enableLiveApi(page);
  const branding = await brandingRoute(page, 200, { name: "Plain Synthetic", logoUrl: null });
  await page.route("**/auth/session", (route) =>
    fulfillJson(route, 401, { detail: "Sign-in required" }),
  );
  await page.goto("/sign-in");
  await expect(page.getByText("Plain Synthetic", { exact: true }).first()).toBeVisible();
  await expect(page.locator('img[src="/brand/kien-mark.svg"]').first()).toBeVisible();
  expectDirectApiBranding(page, branding);
});

test("branding 404 shows the unknown firm page", async ({ page }) => {
  await enableLiveApi(page);
  const branding = await brandingRoute(page, 404, { detail: "Unknown firm portal" });
  await page.route("**/auth/session", (route) =>
    fulfillJson(route, 401, { detail: "Sign-in required" }),
  );
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Unknown firm" })).toBeVisible();
  await expect(page.locator("main#main-content")).toHaveAttribute(
    "data-tenant-reason",
    "unlisted",
  );
  await expect(page.getByRole("heading", { name: "Sign in to Kien", exact: true })).toHaveCount(0);
  expectDirectApiBranding(page, branding);
});

test("a 403 for another firm's session shows wrong portal and signs out", async ({
  page,
}) => {
  await enableLiveApi(page);
  const branding = await brandingRoute(page, 200, {
    name: "Synthetic Alpha Securities",
    logoUrl: "/brand/kynetic-mark.svg",
  });
  await page.route("**/auth/session", (route) =>
    fulfillJson(route, 403, {
      detail: "Session firm does not match this portal",
    }),
  );
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Wrong portal" })).toBeVisible();
  await expect(page.getByText("one firm at a time")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Example Securities LLC (synthetic)" }),
  ).toHaveCount(0);

  await page.route("**/auth/sign-out", (route) => {
    expect(route.request().method()).toBe("POST");
    expect(new URL(route.request().url()).pathname).toBe("/auth/sign-out");
    return route.fulfill({ status: 204, body: "" });
  });
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByRole("heading", { name: "Sign in to Kien", exact: true })).toBeVisible();
  expectDirectApiBranding(page, branding);
});
