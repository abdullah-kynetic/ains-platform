import { test, expect } from "./fixtures";

test("questionnaire only confirms what applies; N/A goes through the reasoned checklist flow", async ({ page }) => {
  await page.goto("/questionnaire");
  await expect(page.getByRole("heading", { name: "Firm questionnaire" })).toBeVisible();
  // The older direct N/A path is gone: there is no "No" answer and nothing is marked N/A here.
  await expect(page.getByRole("button", { name: /^No/ })).toHaveCount(0);
  await expect(page.getByText("mark N/A", { exact: false })).toHaveCount(0);
  await expect(page.getByText("Marked N/A")).toHaveCount(0);
  await expect(page.getByRole("link", { name: "document checklist" }).first()).toBeVisible();
  for (const button of await page.getByRole("button", { name: "Yes, this applies" }).all()) await button.click();
  await page.getByRole("button", { name: "Save answers" }).click();
  await expect(page.getByRole("status")).toContainText("Answers saved");
  await page.getByRole("link", { name: "document checklist" }).first().click();
  await expect(page).toHaveURL(/\/checklist$/);
});
