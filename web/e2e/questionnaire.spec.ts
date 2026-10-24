import { test, expect } from "@playwright/test";

test("questionnaire saves representations and blocks uploads while N/A is pending", async ({ page }) => {
  await page.goto("/questionnaire");
  await expect(page.getByRole("heading", { name: "Firm questionnaire" })).toBeVisible();
  const yesButtons = page.getByRole("button", { name: "Yes, this applies" });
  for (const button of await yesButtons.all()) await button.click();
  await page.getByRole("button", { name: "No — auditor review" }).nth(2).click();
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Save answers" }).click();
  await expect(page.getByRole("status")).toContainText("Answers saved");
  await page.reload();
  await expect(page.getByText("N/A awaiting Quentin")).toBeVisible();
  await page.goto("/checklist");
  await expect(page.getByText("N/A or no-activity confirmation awaiting auditor review", { exact: false })).toBeVisible();
  await page.goto("/upload");
  await expect(page.getByLabel("Request", { exact: true }).locator('option[value="AML-BD-012"]')).toHaveCount(0);
});
