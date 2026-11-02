import { test, expect } from "./fixtures";

test("auditor task completion persists without finalizing audit work", async ({
  page,
}) => {
  await page.goto("/");
  await page.evaluate(() => localStorage.setItem("ains-synthetic-role", "auditor"));
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

test("auditor can create and edit a synthetic internal task", async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => localStorage.setItem("ains-synthetic-role", "auditor"));
  await page.goto("/auditor");

  await page.getByRole("button", { name: "Add task" }).click();
  await page.getByLabel("Task title").fill("Prepare synthetic status brief");
  await page.getByLabel("Task request ID").fill("AML-BD-004");
  await page.getByLabel("Task due date").fill("2026-12-20");
  await page.getByLabel("Task priority").selectOption("high");
  await page.getByRole("button", { name: "Save task" }).click();

  await expect(page.getByText("Prepare synthetic status brief")).toBeVisible();
  await page.reload();
  await expect(page.getByText("Prepare synthetic status brief")).toBeVisible();

  await page.getByRole("button", { name: "Edit Prepare synthetic status brief" }).click();
  await page.getByLabel("Task title").fill("Finalize synthetic status brief");
  await page.getByLabel("Task priority").selectOption("low");
  await page.getByRole("button", { name: "Save task" }).click();
  const updatedTask = page.getByRole("listitem").filter({ hasText: "Finalize synthetic status brief" });
  await expect(updatedTask).toBeVisible();
  await expect(updatedTask.getByText("low priority")).toBeVisible();
});
