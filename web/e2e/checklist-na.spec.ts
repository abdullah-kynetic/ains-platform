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


test("client marks and undoes numbered N/A; auditor sees client attribution", async ({ page }) => {
  await page.goto("/checklist");
  const toggle = page.getByRole("button", { name: "Mark N/A AML-BD-001", exact: true });
  await toggle.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByText("1 of 32 requests resolved (receipts or N/A)")).toBeVisible();
  await expect(page.locator("details").last()).toContainText("AML-BD-001");
  await expect(page.getByText("Marked N/A by client", {exact:true})).toBeVisible();
  await page.reload();
  await expect(page.getByRole("button", {name:"Undo N/A AML-BD-001",exact:true})).toBeVisible();
  await page.evaluate(() => localStorage.setItem("ains-synthetic-role", "auditor"));
  await page.goto("/auditor/engagements/eng-synthetic-001");
  await expect(page.locator("details").filter({has:page.locator("summary",{hasText:"AML-BD-001 —"})})).toContainText("Marked N/A by client");
  await page.evaluate(() => localStorage.setItem("ains-synthetic-role", "client"));
  await page.goto("/checklist");
  await page.getByRole("button", {name:"Undo N/A AML-BD-001",exact:true}).click();
  await expect(page.getByText("0 of 32 requests resolved (receipts or N/A)")).toBeVisible();
  await expect(page.locator("details").first()).toContainText("AML-BD-001");
});

test("client N/A remains accessible on phone in dark mode", async ({ page }) => {
  await page.setViewportSize({width:390,height:844});
  await page.emulateMedia({reducedMotion:"reduce"});
  await page.goto("/checklist");
  await page.evaluate(() => localStorage.setItem("ains-theme","dark"));
  await page.reload();
  await page.getByRole("button",{name:"Mark N/A AML-BD-001",exact:true}).click();
  await expect(page.getByText("Marked N/A by client",{exact:true})).toBeVisible();
  await expect(page.getByRole("button",{name:"Undo N/A AML-BD-001",exact:true})).toBeEnabled();
  const { default: AxeBuilder } = await import("@axe-core/playwright");
  const result = await new AxeBuilder({page}).withTags(["wcag2a","wcag2aa","wcag21aa"]).analyze();
  expect(result.violations).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
