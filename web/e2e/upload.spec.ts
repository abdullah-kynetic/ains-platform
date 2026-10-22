import { test, expect } from "@playwright/test";
import { createHash } from "node:crypto";

test("central upload confirms multiple destinations and preserves receipts", async ({ page }) => {
  await page.goto("/upload");
  await page.getByLabel("Search requests").fill("AML-BD-001");
  await page.getByLabel("Request", { exact: true }).selectOption("AML-BD-001");
  const body = Buffer.from("Synthetic evidence only");
  await page.getByLabel("Select synthetic files").setInputFiles([
    { name: "synthetic.txt", mimeType: "text/plain", buffer: body },
    { name: "synthetic.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.7 synthetic") },
    { name: "unsupported.exe", mimeType: "application/octet-stream", buffer: Buffer.from("synthetic") },
  ]);
  await page.getByLabel("Destination for synthetic.pdf").selectOption("AML-BD-002");
  await expect(page.getByRole("button", { name: "Confirm and upload" })).toBeDisabled();
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Confirm and upload" }).click();
  await expect(page.getByRole("status", { name: "" }).filter({ hasText: /^Received$/ })).toHaveCount(2);
  await expect(page.getByRole("alert").filter({ hasText: "Wrong file type" })).toBeVisible();
  await expect(page.getByText(`SHA-256: ${createHash("sha256").update(body).digest("hex")}`, { exact: false })).toBeVisible();
  await page.goto("/checklist");
  await expect(page.getByText("synthetic.txt", { exact: true })).toBeVisible();
  await expect(page.getByText("synthetic.pdf", { exact: true })).toBeVisible();
  await expect(page.locator('input[type="file"]')).toHaveCount(0);
});
