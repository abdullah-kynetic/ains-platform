import { test, expect } from "@playwright/test";

test("manual auditor decision stays internal while neutral replacement feedback reaches client", async ({
  page,
}) => {
  await page.goto("/upload");
  await page
    .getByLabel("Select synthetic files")
    .setInputFiles({
      name: "synthetic.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("Synthetic manual review fixture"),
    });
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Confirm and upload" }).click();
  await expect(
    page.getByRole("status").filter({ hasText: /^Received$/ }),
  ).toBeVisible();
  // Seed assigned evidence to exercise the existing auditor review workflow independently
  // of the client upload center, which now receives unassigned engagement files.
  await page.evaluate(() => {
    const key = "ains-synthetic-engagement-v1";
    const data = JSON.parse(localStorage.getItem(key)!);
    const item = data.sections
      .flatMap(
        (section: {
          items: { id: string; files: unknown[]; status: string }[];
        }) => section.items,
      )
      .find((item: { id: string }) => item.id === "AML-BD-001");
    item.files.push(...data.unassignedDocuments);
    item.status = "checking";
    data.unassignedDocuments = [];
    localStorage.setItem(key, JSON.stringify(data));
  });
  await page.evaluate(() =>
    localStorage.setItem("ains-synthetic-role", "auditor"),
  );
  await page.goto("/auditor");
  await page.getByRole("link", { name: "Open audit workspace" }).click();
  await page.locator("summary").filter({ hasText: "AML-BD-001:" }).click();
  await expect(page.getByText("synthetic.txt", { exact: true })).toBeVisible();
  await page
    .getByLabel("Evidence assessment AML-BD-001", { exact: true })
    .selectOption("conflicting");
  await page
    .getByLabel("Internal notes AML-BD-001", { exact: true })
    .fill("Synthetic private reasoning");
  await page
    .getByRole("button", { name: "Save decision AML-BD-001", exact: true })
    .click();
  await expect(page.getByText("Saved. History updated.")).toBeVisible();
  await expect(
    page.getByText("request.manual_decision", { exact: false }),
  ).toBeVisible();
  await page
    .getByLabel("Intake feedback for synthetic.txt")
    .selectOption("unreadable");
  await expect(
    page.getByText("document.feedback", { exact: false }),
  ).toBeVisible();
  await page.getByRole("button", { name: /Kien Operations/ }).click();
  await page.getByRole("button", { name: /Example Securities LLC/ }).click();
  await page.goto("/checklist");
  await expect(
    page.getByText("Please replace this file with a readable copy.").first(),
  ).toBeVisible();
  await expect(page.getByText("Synthetic private reasoning")).toHaveCount(0);
});
