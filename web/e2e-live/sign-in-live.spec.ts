import { execFileSync } from "node:child_process";
import { expect, test, type Page } from "@playwright/test";

// Synthetic users seeded by scripts/e2e_backend.py. Test-only values.
const CLIENT = "e2e-client@example.test";
const AUDITOR = "e2e-auditor@example.test";
const LOCKOUT = "e2e-lockout@example.test";
const CLIENT_PASSWORD = "synthetic-client-password";
const AUDITOR_PASSWORD = "synthetic-auditor-password";
const MFA_SECRET = "JBSWY3DPEHPK3PXP";
const INVITE_TOKEN = "synthetic-invitation-token-0123456789abcdef";

function totp(): string {
  return execFileSync(
    "../.venv/bin/python",
    ["-c", `import pyotp,sys;print(pyotp.TOTP("${MFA_SECRET}").now())`],
    { encoding: "utf8" },
  ).trim();
}

/** The form's own alert, not Next.js's route announcer (also role=alert). */
function alertText(page: Page) {
  return page.locator("p[role=alert]");
}

/** Session status as the browser sees it (cookie included). */
async function sessionStatus(page: Page): Promise<number> {
  return page.evaluate(
    async (url) => (await fetch(url, { credentials: "include" })).status,
    "http://kynetic.localhost:8000/auth/session",
  );
}

async function fillCredentials(page: Page, email: string, password: string) {
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
}

test("signed-out visitors are sent to sign-in and keep their destination", async ({ page }) => {
  await page.goto("/auditor?tab=tasks");
  await expect(page).toHaveURL(/\/sign-in\?next=%2Fauditor%3Ftab%3Dtasks/);
});

test("client signs in with a password and lands on the portal", async ({ page }) => {
  await page.goto("/sign-in");
  await fillCredentials(page, CLIENT, CLIENT_PASSWORD);
  await expect(page).not.toHaveURL(/sign-in/);
  expect(await sessionStatus(page)).toBe(200);
});

test("wrong password gives one generic message, never which part was wrong", async ({ page }) => {
  await page.goto("/sign-in");
  await fillCredentials(page, CLIENT, "not-the-password");
  await expect(alertText(page)).toHaveText("Email or password is incorrect");
  await page.getByLabel("Email", { exact: true }).fill("nobody@example.test");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(alertText(page)).toHaveText("Email or password is incorrect");
});

test("auditor needs MFA: wrong code is rejected, right code returns to next", async ({ page }) => {
  await page.goto("/sign-in?next=%2Fauditor");
  await fillCredentials(page, AUDITOR, AUDITOR_PASSWORD);
  const code = page.getByLabel("Authenticator or recovery code");
  await expect(code).toBeVisible();
  await code.fill("000000");
  await page.getByRole("button", { name: "Verify", exact: true }).click();
  await expect(alertText(page)).toContainText("code is not valid");
  await code.fill(totp());
  await page.getByRole("button", { name: "Verify", exact: true }).click();
  await expect(page).toHaveURL(/\/auditor$/);
});

test("an external next target is ignored", async ({ page }) => {
  await page.goto("/sign-in?next=%2F%2Fevil.invalid");
  await fillCredentials(page, CLIENT, CLIENT_PASSWORD);
  await expect(page).toHaveURL(/kynetic.localhost:3100\/(?!\/)/);
  expect(new URL(page.url()).hostname).toBe("kynetic.localhost");
});

test("repeated failures lock the account with a wait message, other users unaffected", async ({ page }) => {
  await page.goto("/sign-in");
  for (let i = 0; i < 5; i++) {
    await fillCredentials(page, LOCKOUT, "wrong-password");
    await expect(alertText(page)).toBeVisible();
  }
  await fillCredentials(page, LOCKOUT, CLIENT_PASSWORD);
  await expect(alertText(page)).toContainText("Too many failed attempts. Try again in about");
  await expect(page).toHaveURL(/sign-in/);
  // The right password still signs in a different account from the same browser.
  await fillCredentials(page, CLIENT, CLIENT_PASSWORD);
  await expect(page).not.toHaveURL(/sign-in/);
});

test("sign-out ends the session", async ({ page }) => {
  await page.goto("/sign-in");
  await fillCredentials(page, CLIENT, CLIENT_PASSWORD);
  await expect(page).not.toHaveURL(/sign-in/);
  // A first sign-in shows the welcome tour; skip it like a user would.
  await page.getByRole("button", { name: "Skip tour" }).click();
  await page.getByRole("button", { name: "Sign out" }).first().click();
  await expect(page).toHaveURL(/sign-in/);
  expect(await sessionStatus(page)).toBe(401);
});

test("invitation: shows the invite, sets a password and signs the client in", async ({ page }) => {
  await page.goto(`/accept-invitation?token=${INVITE_TOKEN}`);
  await expect(page.getByRole("heading", { name: "Accept client invitation" })).toBeVisible();
  await expect(page.getByText("Synthetic E2E Securities")).toBeVisible();
  await page.getByLabel("Create password").fill("a-new-synthetic-password-1");
  await page.getByLabel("Confirm password").fill("a-new-synthetic-password-1");
  await page.getByRole("button", { name: "Set password and activate account" }).click();
  await expect(page).not.toHaveURL(/accept-invitation/);
  // The token is single use.
  await page.goto(`/accept-invitation?token=${INVITE_TOKEN}`);
  await expect(page.getByText(/unavailable|used|invalid/i).first()).toBeVisible();
});
