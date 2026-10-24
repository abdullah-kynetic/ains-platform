import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("auditor audit log filters, verifies and passes axe", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("ains-synthetic-role", "auditor"));
  await page.goto("/auditor/audit-log");
  await expect(page.getByRole("heading", { name: "Audit Log", exact: true })).toBeVisible();
  await expect(page.getByText("engagement.view", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Verify chain" }).click();
  await expect(page.getByRole("status")).toContainText("Chain verified");
  await page.getByLabel("Action", { exact: true }).fill("missing.action");
  await expect(page.getByText("No audit entries match these filters.")).toBeVisible();
  await page.getByLabel("Action", { exact: true }).fill("");
  await expect(page.getByText("engagement.view", { exact: true })).toBeVisible();
  expect((await new AxeBuilder({ page }).exclude("nextjs-portal").withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze()).violations).toEqual([]);
});
