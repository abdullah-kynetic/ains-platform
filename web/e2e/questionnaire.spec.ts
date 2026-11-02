import { test, expect } from "@playwright/test";

test("questionnaire directly marks N/A and blocks uploads for that request", async ({ page }) => {
  await page.goto("/questionnaire");
  await expect(page.getByRole("heading", { name: "Firm questionnaire" })).toBeVisible();
  const yesButtons = page.getByRole("button", { name: "Yes, this applies" });
  for (const button of await yesButtons.all()) await button.click();
  await page.getByRole("button", { name: "No: mark N/A" }).nth(2).click();
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Save answers" }).click();
  await expect(page.getByRole("status")).toContainText("Answers saved");
  await page.reload();
  await expect(page.getByText("Marked N/A")).toBeVisible();
  await page.goto("/checklist");
  await expect(page.getByText("Marked N/A by client", { exact: false })).toBeVisible();
  await page.goto("/upload");
  await expect(page.getByLabel("Request", { exact: true }).locator('option[value="AML-BD-012"]')).toHaveCount(0);
});
