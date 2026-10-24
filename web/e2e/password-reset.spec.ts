import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("synthetic recovery never sends email and is accessible", async ({ page }) => {
  let requests = 0;
  await page.route("**/auth/password-reset/**", (route) => {
    requests += 1;
    return route.abort();
  });
  await page.goto("/reset-password");
  await page.getByLabel("Email", { exact: true }).fill("synthetic@example.test");
  await page.getByRole("button", { name: "Email reset link" }).click();
  await expect(page.getByRole("status")).toContainText("Synthetic demo only");
  expect(requests).toBe(0);
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
});

test("recovery token form validates matching passwords", async ({ page }) => {
  await page.goto("/reset-password?token=synthetic-token");
  await expect(page.getByLabel("New password", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Confirm password", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Back to sign in" }).click();
  await expect(page).toHaveURL(/sign-in/);
});
