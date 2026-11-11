import { test, expect } from "./fixtures";

test("isolation proof page explains itself and needs the real backend to run", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("ains-synthetic-role", "auditor"));
  await page.goto("/auditor/isolation");
  await expect(page.getByRole("heading", { name: "Firm isolation proof", exact: true })).toBeVisible();
  await expect(page.getByText("Synthetic demo build")).toBeVisible();
  await expect(page.getByRole("button", { name: "Run isolation check" })).toBeDisabled();
  await expect(page.getByText("tests/test_two_practice_isolation.py")).toBeVisible();
});
