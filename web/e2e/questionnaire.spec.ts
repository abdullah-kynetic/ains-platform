import { test, expect } from "./fixtures";

test("questionnaire directly marks N/A and blocks uploads for that request", async ({ page }) => {
  await page.goto("/questionnaire");
  await expect(page.getByRole("heading", { name: "Firm questionnaire" })).toBeVisible();
  const yesButtons = page.getByRole("button", { name: "Yes, this applies" });
  for (const button of await yesButtons.all()) await button.click();
  await page.getByRole("button", { name: "No — mark N/A" }).nth(2).click();
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Save answers" }).click();
  await expect(page.getByRole("status")).toContainText("Answers saved");
  await page.reload();
  await expect(page.getByText("Marked N/A")).toBeVisible();
  await page.goto("/checklist");
  await expect(page.getByText("Marked N/A by client", { exact: false })).toBeVisible();
  await page.goto("/upload");
  // Client uploads are unassigned; the auditor picker must exclude N/A requests.
  await expect(page.getByLabel("Request", { exact: true })).toHaveCount(0);
  await page.evaluate(() => localStorage.setItem("ains-synthetic-role", "auditor"));
  await page.reload();
  const requests = page.getByLabel("Request", { exact: true });
  await expect(requests).toBeVisible();
  await expect(requests.locator('option[value="AML-BD-001"]')).toHaveCount(1);
  await expect(requests.locator('option[value="AML-BD-012"]')).toHaveCount(0);
});
