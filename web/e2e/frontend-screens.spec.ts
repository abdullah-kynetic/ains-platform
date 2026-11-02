import { expect, test, type Page } from "@playwright/test";

const E = "/auditor/engagements/eng-synthetic-001";
const asRole = (page: Page, role: "auditor" | "client") =>
  page.addInitScript((r) => localStorage.setItem("ains-synthetic-role", r), role);

test.describe("auditor workspace (synthetic)", () => {
  test.beforeEach(async ({ page }) => { await asRole(page, "auditor"); });

  test("sidebar groups and engagement tabs", async ({ page }) => {
    await page.goto(E);
    const nav = page.getByRole("navigation").first();
    for (const group of ["Workspace", "Engagements", "Firm"]) await expect(nav.locator("p.nav-label", { hasText: new RegExp(`^${group}$`) })).toBeVisible();
    for (const tab of ["Overview", "Requests", "Documents", "Checklist", "Workpapers", "Samples", "Findings", "Report", "Independence", "Sign-off", "Activity"])
      await expect(page.getByRole("navigation", { name: "Tabs" }).getByRole("link", { name: tab })).toBeVisible();
  });

  test("checklist sorts Does not apply last and persists a change", async ({ page }) => {
    await page.goto(`${E}/checklist`);
    const rows = page.getByRole("row");
    await expect(rows).toHaveCount(35);
    await expect(rows.last()).toContainText("Does not apply");
    await page.getByLabel(/Conclusion for AML-BD-018/).selectOption("fail");
    await page.reload();
    await expect(page.getByLabel(/Conclusion for AML-BD-018/)).toHaveValue("fail");
  });

  test("a finding cannot be approved without a citation", async ({ page }) => {
    await page.goto(`${E}/findings`);
    await page.getByRole("button", { name: "New finding" }).first().click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel("Title").fill("Test finding");
    await dialog.getByLabel("Rule cited").fill("FINRA Rule 3310(c)");
    await dialog.getByLabel("Condition").fill("Condition");
    await dialog.getByLabel("Cause", { exact: true }).fill("Cause");
    await dialog.getByLabel("Effect").fill("Effect");
    await dialog.getByLabel("Recommendation").fill("Recommendation");
    await dialog.getByRole("button", { name: "Save draft" }).click();
    const card = page.locator("[data-slot=card]", { hasText: "Test finding" });
    await card.getByRole("button", { name: "Approve" }).click();
    await expect(page.getByText("Cite at least one document and page.")).toBeVisible();
  });

  test("sign-off needs reviewer approval, a typed name and a signature before completion", async ({ page }) => {
    await page.goto("/auditor/engagements/eng-synthetic-005/sign-off");
    await page.getByRole("button", { name: "Approve as second reviewer" }).click();
    await expect(page.getByText(/Approved /)).toBeVisible();
    const sign = page.getByRole("button", { name: "Sign report" });
    await expect(sign).toBeDisabled();
    await page.getByLabel(/reviewed this report/).check();
    await page.getByLabel(/to sign/).fill("Quentin");
    await sign.click();
    await page.getByRole("button", { name: "Mark complete" }).click();
    await expect(page.getByText(/Completed /)).toBeVisible();
  });

  test("global search finds a client and a finding", async ({ page }) => {
    await page.goto("/auditor");
    await page.getByRole("button", { name: "Search workspace" }).click();
    await page.getByLabel("Search pages").fill("Harborview");
    await expect(page.getByRole("button", { name: /Harborview Securities/ }).first()).toBeVisible({ timeout: 15000 });
    await page.getByLabel("Search pages").fill("risk assessment");
    await expect(page.getByRole("button", { name: /AML risk assessment not updated/ })).toBeVisible({ timeout: 15000 });
  });

  test("firm settings and notifications load", async ({ page }) => {
    await page.goto("/auditor/firm/templates");
    await expect(page.getByText("Retail broker-dealer").first()).toBeVisible();
    await page.goto("/auditor/notifications");
    await page.getByRole("button", { name: "Mark all as read" }).click();
    await expect(page.getByRole("button", { name: "Mark all as read" })).toBeDisabled();
  });
});

test.describe("client portal results (synthetic)", () => {
  test("client sees only released requests, never findings", async ({ page }) => {
    await asRole(page, "client");
    await expect(async () => { const r = await page.goto("/findings"); expect(r?.status()).toBe(404); }).toPass();
    await page.goto("/responses");
    await expect(page.getByRole("heading", { name: "Responses requested" })).toBeVisible();
    for (const leaked of ["Training records missing", "Cause", "Condition", "Severity", "FINRA Rule"]) await expect(page.getByText(leaked)).toHaveCount(0);
    await page.getByLabel("Your response").fill("We agree and will fix this by year end.");
    await page.getByRole("button", { name: "Submit response" }).click();
    await expect(page.getByText("We agree and will fix this by year end.")).toBeVisible();
    await page.goto("/report");
    await expect(page.getByText("2025 report not signed yet")).toBeVisible();
    await page.goto("/invoices");
    await expect(page.getByText("KIEN-0007")).toBeVisible();
  });
});
