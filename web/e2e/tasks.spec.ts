import { test, expect } from "@playwright/test";

test("auditor task completion persists without finalizing audit work", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Example Securities LLC/ }).click();
  await page.getByRole("button", { name: /AINS Operations/ }).click();
  await page.goto("/auditor");

  const task = page.getByRole("checkbox", {
    name: "Mark Review newly uploaded program evidence complete",
  });
  await expect(task).toBeVisible();
  await task.check();
  await expect(task).toBeChecked();

  await page.reload();
  await expect(task).toBeChecked();
  await expect(page.getByText("Completion never finalizes a finding.")).toBeVisible();
});
