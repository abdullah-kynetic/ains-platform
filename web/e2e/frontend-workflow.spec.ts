import { expect, test } from "@playwright/test";

test("auditor can review document context and see report blockers", async ({ page }) => {
  await page.goto("/auditor?demo=auditor");
  await page.getByRole("link", { name: "Open engagement", exact: true }).click();
  await expect(page.getByText("Engagement progress", { exact: true })).toBeVisible();
  await page.getByRole("tab", { name: "Documents", exact: true }).click();
  await expect(page.getByText("AML-BD-034 ·", { exact: false })).toBeVisible();
  await page.getByRole("textbox", { name: "Search documents" }).fill("AML-BD-003");
  await page.getByRole("button", { name: "Review document", exact: true }).click();
  await expect(page.getByText("Document summary", { exact: true })).toBeVisible();
  await expect(page.getByText("Source evidence", { exact: true })).toBeVisible();
  await expect(page.getByText("synthetic-aml-bd-003.txt · Page 1", { exact: true })).toBeVisible();
  await page.getByLabel("Review reason category").selectOption("business_context");
  await page.getByLabel("Decision notes").fill("Synthetic firm had no new clients in the selected month.");
  await page.getByRole("button", { name: "Save document decision" }).click();
  await expect(page.locator("p").filter({ hasText: "Synthetic firm had no new clients in the selected month." })).toBeVisible();
  await page.getByRole("tab", { name: "Report readiness" }).click();
  await expect(page.getByRole("button", { name: "Generate draft report" })).toBeDisabled();
  await page.getByRole("button", { name: "Preview report layout" }).click();
  await expect(page.getByText("SYNTHETIC LAYOUT PREVIEW · UNSIGNED", { exact: true })).toBeVisible();
  await page.getByLabel("Color theme").selectOption("light");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.getByRole("tab", { name: "Review feedback", exact: true }).click();
  await expect(page.locator("p").filter({ hasText: "Synthetic firm had no new clients in the selected month." })).toBeVisible();
  await page.getByRole("button", { name: "Client view", exact: true }).click();
  await expect(page.getByText("Synthetic firm had no new clients in the selected month.", { exact: true })).toHaveCount(0);
  await page.getByRole("link", { name: "Progress", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Your document progress" })).toBeVisible();
});

test("auditor dashboard and pipeline fit a phone viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/auditor/engagements/eng-synthetic-001?demo=auditor");
  await expect(page.getByText("Engagement progress", { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByRole("tab", { name: "AI processing (2)" }).click();
  await expect(page.getByText("Extracting document text · 42s elapsed", { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("client progress contains no internal assessment or correction tools", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/progress?demo=client");
  await expect(page.getByRole("heading", { name: "Your document progress" })).toBeVisible();
  await expect(page.getByText("Source evidence", { exact: true })).toHaveCount(0);
  await expect(page.getByLabel("Decision notes")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Save document decision" })).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
