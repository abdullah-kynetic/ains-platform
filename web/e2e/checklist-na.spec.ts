import { test, expect } from "@playwright/test";

test("auditor NA moves to bottom, updates progress, persists and undo restores state", async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => localStorage.setItem("ains-synthetic-role", "auditor"));
  await page.goto("/auditor/engagements/eng-synthetic-001");
  const request = page.locator("details").filter({has: page.locator("summary", {hasText: "AML-BD-001 —"})});
  await request.locator("summary").click();
  await request.getByRole("button", {name: "Does not apply", exact:true}).click();
  await expect(request.getByRole("button", {name: "Undo does not apply"})).toBeVisible();
  await expect(page.locator("details").filter({has: page.locator("summary", {hasText: /^AML-BD-/})}).last()).toContainText("AML-BD-001");
  await page.evaluate(() => localStorage.setItem("ains-synthetic-role", "client"));
  await page.goto("/checklist");
  await expect(page.getByText("1 of 32 requests resolved (receipts or N/A)")).toBeVisible();
  const na = page.locator("details").filter({has:page.locator("summary", {hasText:"Does not apply"})});
  await expect(na).toContainText("AML-BD-001");
  await expect(page.locator("details").last()).toContainText("AML-BD-001");
  await expect(page.getByRole("button",{name:"Undo does not apply"})).toHaveCount(0);
  await page.reload(); await expect(na).toContainText("AML-BD-001");
  await page.evaluate(() => localStorage.setItem("ains-synthetic-role", "auditor"));
  await page.goto("/auditor/engagements/eng-synthetic-001");
  await request.locator("summary").click();
  await request.getByRole("button", {name: "Undo does not apply"}).click();
  await expect(request.getByRole("button", {name: "Does not apply", exact:true})).toBeVisible();
  await page.evaluate(() => localStorage.setItem("ains-synthetic-role", "client"));
  await page.goto("/checklist");
  await expect(page.getByText("0 of 32 requests resolved (receipts or N/A)")).toBeVisible();
  await expect(page.locator("details").first()).toContainText("AML-BD-001");
});
