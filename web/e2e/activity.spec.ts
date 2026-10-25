import { test, expect } from "@playwright/test";

test("auditor activity links to assigned work without exposing audit details", async ({
  page,
}) => {
  await page.goto("/");
  await page.evaluate(() => localStorage.setItem("ains-synthetic-role", "auditor"));
  await page.goto("/auditor");

  await expect(page.getByRole("heading", { name: "Latest activity" })).toBeVisible();
  await expect(page.getByText("Internal only", { exact: true })).toBeVisible();
  await expect(page.getByText("Internal auditor decision recorded", { exact: true })).toBeVisible();
  await expect(page.getByText("Synthetic private reasoning")).toHaveCount(0);

  await page
    .getByRole("region", { name: "Latest activity" })
    .getByRole("link", { name: "AML-BD-001", exact: true })
    .click();
  await expect(page.getByRole("heading", { name: "Example Securities LLC (synthetic)" })).toBeVisible();
});
