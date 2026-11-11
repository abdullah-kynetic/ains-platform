import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() =>
    localStorage.setItem("ains-synthetic-signed-out", "true"),
  );
});

test("auditor signs in with credentials together and returns to next", async ({
  page,
}) => {
  await page.goto("/sign-in?next=%2Fauditor");
  await expect(page.getByLabel("Password", { exact: true })).toBeVisible();
  await expect(page.getByText("Forgot password?")).toBeVisible();
  await page
    .getByLabel("Email", { exact: true })
    .fill("auditor@example.invalid");
  await page
    .getByLabel("Password", { exact: true })
    .fill("synthetic-only-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/auditor$/);
});

test("invalid next falls back home", async ({ page }) => {
  await page.goto("/sign-in?next=%2F%2Fevil.invalid");
  await page
    .getByLabel("Email", { exact: true })
    .fill("client@example.invalid");
  await page
    .getByLabel("Password", { exact: true })
    .fill("synthetic-only-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(new URL("/", page.url()).href);
});

test("protected paths set next and invitation acceptance has its own page", async ({
  page,
}) => {
  await page.goto("/auditor?tab=tasks");
  await expect(page).toHaveURL(/\/sign-in\?next=%2Fauditor%3Ftab%3Dtasks/);
  await page.goto("/accept-invitation");
  await expect(
    page.getByRole("heading", { name: "Accept client invitation" }),
  ).toBeVisible();
});

test("API password challenge sends credentials together and verifies the emailed code", async ({
  page,
}) => {
  await page.addInitScript(() =>
    localStorage.setItem("ains-e2e-live-api", "1"),
  );
  const user = {
    id: "synthetic-auditor",
    email: "auditor@example.invalid",
    name: "Synthetic Auditor",
    role: "auditor",
    firm_id: null,
  };
  let signedIn = false;
  const payloads: unknown[] = [];
  await page.route("**/tenant/branding", (route) =>
    route.fulfill({ json: { name: "Synthetic Firm", logoUrl: null } }),
  );
  await page.route("**/auth/session", (route) =>
    route.fulfill({
      status: signedIn ? 200 : 401,
      json: signedIn ? { user } : { detail: "Sign-in required" },
    }),
  );
  await page.route("**/auth/password", (route) => {
    const payload = route.request().postDataJSON();
    payloads.push(payload);
    signedIn = payload.code === "123456";
    return route.fulfill({
      status: signedIn ? 200 : 401,
      json: signedIn ? { user } : { detail: "Email code required" },
    });
  });
  await page.goto("/sign-in?next=%2Fauditor");
  await page.getByLabel("Email", { exact: true }).fill(user.email);
  expect(payloads).toEqual([]);
  await page
    .getByLabel("Password", { exact: true })
    .fill("synthetic-only-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByText(`We emailed a 6-digit code to ${user.email}`)).toBeVisible();
  await page.getByLabel("6-digit code from your email").fill("123456");
  await page.getByLabel("Remember this browser for 30 days").check();
  await page.getByRole("button", { name: "Verify", exact: true }).click();
  await expect(page).toHaveURL(/\/auditor$/);
  expect(payloads).toEqual([
    {
      email: user.email,
      password: "synthetic-only-password",
      code: null,
      remember_device: false,
    },
    {
      email: user.email,
      password: "synthetic-only-password",
      code: "123456",
      remember_device: true,
    },
  ]);
});

test("credentials validate email before sign in", async ({ page }) => {
  await page.goto("/sign-in");
  await expect(page.getByLabel("Password", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Forgot password?" }),
  ).toBeVisible();
  await page.getByLabel("Email", { exact: true }).fill("invalid");
  await page
    .getByLabel("Password", { exact: true })
    .fill("synthetic-only-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByLabel("Email", { exact: true })).toBeVisible();
  await expect(page.getByLabel("6-digit code from your email")).toHaveCount(
    0,
  );
});
