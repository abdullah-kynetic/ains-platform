import { test, expect } from "./fixtures";

/** Synthetic (mock build) coverage of the demo workflow screens; the real-backend journey is web/e2e-live/demo-journey-live.spec.ts. */
const ENG = "eng-synthetic-001";

async function asRole(page: import("@playwright/test").Page, role: "auditor" | "client") {
  await page.goto("/");
  await page.evaluate((r) => localStorage.setItem("ains-synthetic-role", r), role);
}

test("step 2: auditor sends the checklist and the client sees it was sent", async ({ page }) => {
  await asRole(page, "client");
  await page.goto("/");
  await expect(page.getByTestId("checklist-status")).toContainText("has not sent the checklist yet");

  await asRole(page, "auditor");
  await page.goto(`/auditor/engagements/${ENG}`);
  const card = page.getByTestId("client-checklist-card");
  await expect(card.getByTestId("workflow-stage")).toHaveText("Checklist not sent");
  await card.getByRole("button", { name: "Send checklist to client" }).click();
  await expect(card.getByTestId("workflow-stage")).toHaveText("Checklist sent");
  await expect(card.getByRole("button", { name: "Send checklist to client" })).toHaveCount(0);

  await asRole(page, "client");
  await page.goto("/checklist");
  await expect(page.getByTestId("checklist-status")).toContainText("Your auditor sent the checklist");
});

test("step 4: client maps an uploaded document to a request and submits; auditor accepts it", async ({ page }) => {
  await asRole(page, "auditor");
  await page.goto(`/auditor/engagements/${ENG}`);
  await page.getByRole("button", { name: "Send checklist to client" }).click();
  await expect(page.getByTestId("workflow-stage")).toHaveText("Checklist sent");

  await asRole(page, "client");
  await page.goto("/upload");
  await page.locator("input[type=file]").setInputFiles({ name: "synthetic-policy.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4 synthetic") });
  await page.getByLabel("I have checked the files for this engagement.").check();
  await page.getByRole("button", { name: "Confirm and upload" }).click();
  await expect(page.getByText("Received", { exact: false }).first()).toBeVisible();

  await page.goto("/checklist");
  const row = page.getByTestId("request-AML-BD-001");
  const select = row.getByLabel("Map a document to AML-BD-001");
  const value = await select.locator("option", { hasText: "synthetic-policy.pdf" }).getAttribute("value");
  await select.selectOption(value!);
  await row.getByRole("button", { name: "Map", exact: true }).click();
  await expect(row.getByLabel("Documents for AML-BD-001")).toContainText("synthetic-policy.pdf");
  await row.getByRole("button", { name: "Submit AML-BD-001 to auditor" }).click();
  await expect(row).toContainText("With auditor");

  await asRole(page, "auditor");
  await page.goto(`/auditor/engagements/${ENG}/client-checklist`);
  const item = page.getByTestId("client-item-AML-BD-001");
  await item.getByRole("button", { name: "Accept AML-BD-001 for testing" }).click();
  await expect(item).toContainText("Accepted for testing");
});

test("step 5: auditor flags a document, the client replies, the auditor resolves", async ({ page }) => {
  await asRole(page, "auditor");
  await page.goto(`/auditor/engagements/${ENG}`);
  await page.getByRole("button", { name: "Send checklist to client" }).click();
  await expect(page.getByTestId("workflow-stage")).toHaveText("Checklist sent");

  await asRole(page, "client");
  await page.goto("/upload");
  await page.locator("input[type=file]").setInputFiles({ name: "synthetic-policy.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4 synthetic") });
  await page.getByLabel("I have checked the files for this engagement.").check();
  await page.getByRole("button", { name: "Confirm and upload" }).click();
  await expect(page.getByText("Received", { exact: false }).first()).toBeVisible();
  await page.goto("/checklist");
  const row = page.getByTestId("request-AML-BD-001");
  const select = row.getByLabel("Map a document to AML-BD-001");
  const value = await select.locator("option", { hasText: "synthetic-policy.pdf" }).getAttribute("value");
  await select.selectOption(value!);
  await row.getByRole("button", { name: "Map", exact: true }).click();
  await row.getByRole("button", { name: "Submit AML-BD-001 to auditor" }).click();
  await expect(row).toContainText("With auditor");

  await asRole(page, "auditor");
  await page.goto(`/auditor/engagements/${ENG}/client-checklist`);
  const item = page.getByTestId("client-item-AML-BD-001");
  await item.getByRole("button", { name: "Flag AML-BD-001" }).click();
  await page.getByLabel("Problem type").selectOption("wrong_year");
  await page.getByLabel(/Note to the client/).fill("This is the 2023 policy. Please send 2025.");
  await page.getByRole("button", { name: "Send to client" }).click();
  await expect(item).toContainText("Needs information");

  await asRole(page, "client");
  await page.goto("/messages");
  const thread = page.locator("[data-testid^=issue-]").first();
  await expect(thread).toContainText("This is the 2023 policy");
  await thread.getByLabel("Reply").fill("Sending the 2025 policy.");
  await thread.getByRole("button", { name: "Send reply" }).click();
  await expect(thread).toContainText("Sending the 2025 policy.");

  await asRole(page, "auditor");
  await page.goto(`/auditor/engagements/${ENG}/client-checklist`);
  const t = page.getByTestId("issue-threads").locator("[data-testid^=issue-]").first();
  await t.getByRole("button", { name: "Mark resolved" }).click();
  await expect(t).toContainText("Resolved");
});
