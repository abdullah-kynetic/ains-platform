import { test, expect } from "@playwright/test";

test("manual auditor decision stays internal while neutral replacement feedback reaches client", async ({ page }) => {
  await page.goto("/upload");
  await page.getByLabel("Request", { exact: true }).selectOption("AML-BD-001");
  await page.getByLabel("Select synthetic files").setInputFiles({ name: "synthetic.txt", mimeType: "text/plain", buffer: Buffer.from("Synthetic manual review fixture") });
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Confirm and upload" }).click();
  await expect(page.getByRole("status").filter({ hasText: /^Received$/ })).toBeVisible();
  await page.getByRole("button", { name: "Switch to auditor demo" }).click();
  await page.getByRole("link", { name: "Open audit workspace" }).click();
  await page.locator("summary").filter({ hasText: "AML-BD-001 —" }).click();
  await expect(page.getByText("synthetic.txt", { exact: true })).toBeVisible();
  await page.getByLabel("Evidence assessment AML-BD-001", { exact: true }).selectOption("conflicting");
  await page.getByLabel("Internal notes AML-BD-001", { exact: true }).fill("Synthetic private reasoning");
  await page.getByRole("button", { name: "Save decision AML-BD-001", exact: true }).click();
  await expect(page.getByText("Saved. History updated.")).toBeVisible();
  await expect(page.getByText("request.manual_decision", { exact: false })).toBeVisible();
  await page.getByLabel("Intake feedback for synthetic.txt").selectOption("unreadable");
  await expect(page.getByText("document.feedback", { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "Switch to client demo" }).click();
  await page.goto("/checklist");
  await expect(page.getByText("Please replace this file with a readable copy.").first()).toBeVisible();
  await expect(page.getByText("Synthetic private reasoning")).toHaveCount(0);
});
