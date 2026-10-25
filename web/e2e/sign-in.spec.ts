import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() =>
    localStorage.setItem("ains-synthetic-signed-out", "true"),
  );
});

test("auditor signs in one field at a time and returns to next", async ({
  page,
}) => {
  await page.goto("/sign-in?next=%2Fauditor");
  await expect(page.getByLabel("Password", { exact: true })).toHaveCount(0);
  await expect(page.getByText("Forgot password?")).toHaveCount(0);
  await page
    .getByLabel("Email", { exact: true })
    .fill("auditor@example.invalid");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByLabel("Email", { exact: true })).toHaveCount(0);
  await expect(
    page.getByText("auditor@example.invalid", { exact: false }),
  ).toBeVisible();
  await page
    .getByLabel("Password", { exact: true })
    .fill("synthetic-only-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByLabel("Password", { exact: true })).toHaveCount(0);
  await page.getByLabel("Authenticator or recovery code").fill("123456");
  await page.getByRole("button", { name: "Verify", exact: true }).click();
  await expect(page).toHaveURL(/\/auditor$/);
});

test("invalid next falls back home", async ({ page }) => {
  await page.goto("/sign-in?next=%2F%2Fevil.invalid");
  await page
    .getByLabel("Email", { exact: true })
    .fill("client@example.invalid");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page
    .getByLabel("Password", { exact: true })
    .fill("synthetic-only-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(new URL("/", page.url()).href);
});

test("setup stays on a separate page and protected paths set next", async ({
  page,
}) => {
  await page.goto("/auditor?tab=tasks");
  await expect(page).toHaveURL(/\/sign-in\?next=%2Fauditor%3Ftab%3Dtasks/);
  await expect(
    page.getByRole("button", { name: "Set up auditor MFA" }),
  ).toHaveCount(0);
  await page.goto("/account-setup");
  await expect(
    page.getByRole("heading", { name: "Set up auditor MFA" }),
  ).toBeVisible();
  await page.goto("/accept-invitation");
  await expect(
    page.getByRole("heading", { name: "Accept client invitation" }),
  ).toBeVisible();
});

test("API password challenge sends credentials together and verifies MFA", async ({
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
    signedIn = payload.mfa_code === "123456";
    return route.fulfill({
      status: signedIn ? 200 : 401,
      json: signedIn ? { user } : { detail: "MFA code required" },
    });
  });
  await page.goto("/sign-in?next=%2Fauditor");
  await page.getByLabel("Email", { exact: true }).fill(user.email);
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  expect(payloads).toEqual([]);
  await page
    .getByLabel("Password", { exact: true })
    .fill("synthetic-only-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByLabel("Authenticator or recovery code").fill("123456");
  await page.getByRole("button", { name: "Verify", exact: true }).click();
  await expect(page).toHaveURL(/\/auditor$/);
  expect(payloads).toEqual([
    { email: user.email, password: "synthetic-only-password", mfa_code: null },
    {
      email: user.email,
      password: "synthetic-only-password",
      mfa_code: "123456",
    },
  ]);
});

test("email validation and change keep later fields hidden", async ({
  page,
}) => {
  await page.goto("/sign-in");
  await page.getByLabel("Email", { exact: true }).fill("invalid");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByLabel("Password", { exact: true })).toHaveCount(0);
  await page
    .getByLabel("Email", { exact: true })
    .fill("client@example.invalid");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page
    .getByLabel("Password", { exact: true })
    .fill("synthetic-only-password");
  await page.getByRole("link", { name: "Change", exact: true }).click();
  await expect(page.getByLabel("Email", { exact: true })).toHaveValue(
    "client@example.invalid",
  );
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByLabel("Password", { exact: true })).toHaveValue("");
});
