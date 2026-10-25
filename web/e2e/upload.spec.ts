import { test, expect } from "@playwright/test";
import { createHash } from "node:crypto";

test("central upload receives unassigned files and preserves receipts", async ({ page }) => {
  await page.goto("/upload");
  await expect(page.getByLabel("Search requests")).toHaveCount(0);
  await expect(page.getByRole("combobox")).toHaveCount(0);
  const body = Buffer.from("Synthetic evidence only");
  await page.getByLabel("Select synthetic files").setInputFiles([
    { name: "synthetic.txt", mimeType: "text/plain", buffer: body },
    { name: "synthetic.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.7 synthetic") },
    { name: "unsupported.exe", mimeType: "application/octet-stream", buffer: Buffer.from("synthetic") },
  ]);
  await expect(page.getByRole("button", { name: "Confirm and upload" })).toBeDisabled();
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Confirm and upload" }).click();
  await expect(page.getByRole("status", { name: "" }).filter({ hasText: /^Received$/ })).toHaveCount(2);
  await expect(page.getByRole("alert").filter({ hasText: "Wrong file type" })).toBeVisible();
  await expect(page.getByText(`SHA-256: ${createHash("sha256").update(body).digest("hex")}`, { exact: false })).toBeVisible();
  await page.reload();
  await expect(page.getByText("synthetic.txt", { exact: true })).toBeVisible();
  await expect(page.getByText("synthetic.pdf", { exact: true })).toBeVisible();

});


test("client can drop multiple files without choosing requests", async ({ page }) => {
  await page.goto("/upload");
  await expect(page.getByRole("heading", { name: "Upload center" })).toBeVisible();
  const transfer = await page.evaluateHandle(() => {
    const data = new DataTransfer();
    data.items.add(new File(["synthetic first"], "synthetic-first.txt", { type: "text/plain" }));
    data.items.add(new File(["synthetic second"], "synthetic-second.txt", { type: "text/plain" }));
    return data;
  });
  await page.getByText("Drop files here or select multiple files.", { exact: false }).dispatchEvent("drop", { dataTransfer: transfer });
  await transfer.dispose();
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Confirm and upload" }).click();
  await expect(page.getByRole("status").filter({ hasText: /^Received$/ })).toHaveCount(2);
});

test("auditor upload center keeps request selection", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("ains-synthetic-role", "auditor"));
  await page.goto("/upload");
  await expect(page.getByLabel("Search requests")).toBeVisible();
  await expect(page.getByLabel("Request", { exact: true })).toBeVisible();
});
