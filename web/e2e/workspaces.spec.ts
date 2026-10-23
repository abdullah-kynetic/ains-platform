import { test, expect } from "@playwright/test";

test("auditor creates an isolated synthetic client workspace without granting access", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Example Securities LLC/ }).click();
  await page.getByRole("button", { name: /AINS Operations/ }).click();
  await page.goto("/auditor");

  await page.getByRole("button", { name: /AINS Operations/ }).click();
  await page.getByRole("link", { name: "Add client workspace" }).click();
  await expect(page.getByRole("heading", { name: "Add client workspace" })).toBeVisible();
  await page.getByLabel("Firm name").fill("Synthetic Gamma Securities");
  await page.getByLabel("Review period start").fill("2026-01-01");
  await page.getByLabel("Review period end").fill("2026-12-31");
  await page.getByLabel("Target due date (optional)").fill("2027-02-15");
  await page.getByRole("button", { name: "Create workspace" }).click();

  await expect(page.getByRole("heading", { name: "Synthetic Gamma Securities is ready" })).toBeVisible();
  await expect(page.getByText("No client login or invitation was created.")).toBeVisible();
  await page.getByRole("link", { name: "Return to review queue" }).click();
  await expect(page.getByRole("heading", { name: "Synthetic Gamma Securities" })).toBeVisible();
});
