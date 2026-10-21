import { expect, test } from "@playwright/test";

test("client and auditor demonstration uses the real checklist without backend calls", async ({ page }) => {
  const backendCalls: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes(":8000")) backendCalls.push(request.url());
  });
  await page.goto("/");
  await expect(page.getByText("Synthetic demo", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Document checklist" }).click();
  await expect(page.getByRole("heading", { name: "Screening and government requests" })).toBeVisible();
  await expect(page.getByText("Financial-crime filings — contact auditor", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Auditor view", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Quinton’s review queue" })).toBeVisible();
  await page.getByRole("link", { name: "Open engagement", exact: true }).click();
  await expect(page.getByText("Synthetic training follow-up", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Accept", exact: true }).click();
  await expect(page.getByText("accepted", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Engagement setup" }).click();
  await page.getByRole("button", { name: "Review requests" }).click();
  await expect(page.locator("summary")).toHaveCount(34);
  await page.getByLabel("Firm name", { exact: true }).fill("Synthetic Demo Firm");
  await page.getByLabel("Firm identifier").fill("synthetic-demo-firm");
  await page.getByLabel("Review period start").fill("2025-01-01");
  await page.getByLabel("Review period end").fill("2025-12-31");
  await page.getByRole("button", { name: "Create draft" }).click();
  await expect(page.getByText("Synthetic Demo Firm — checklist review", { exact: true })).toBeVisible();
  await page.getByRole("textbox").last().fill("Synthetic review completed for demonstration only.");
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Approve and publish requests" }).click();
  await expect(page.getByRole("button", { name: "Approve and publish requests" })).toHaveCount(0);
  expect(backendCalls).toEqual([]);
});

test("direct auditor link opens the synthetic auditor workspace", async ({ page }) => {
  await page.goto("/auditor?demo=auditor");
  await expect(page.getByRole("heading", { name: "Quinton’s review queue" })).toBeVisible();
});
