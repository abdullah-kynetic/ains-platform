import { expect, test } from "@playwright/test";
import { backend, OTHER_ENGAGEMENT, signIn } from "./helpers";

test("pipeline stage persists on the server and foreign movement is denied", async ({ page }) => {
  await signIn(page);
  await page.goto("/auditor/pipeline");
  const stage = page.getByLabel("Move Synthetic E2E Securities to stage");
  await expect(stage).toBeVisible();
  await expect(page.locator(".stat-card").filter({ hasText: "Due soon" }).locator(".type-metric")).toHaveText("1");
  const target = await stage.inputValue() === "auditor_review" ? "document_collection" : "auditor_review";
  await stage.selectOption(target);
  await expect(page.getByRole("status")).toContainText("Synthetic E2E Securities moved");
  await page.reload();
  await expect(stage).toHaveValue(target);
  await expect(page.getByText("Synthetic preview", { exact: true })).toHaveCount(0);
  await expect(page.getByText("Synthetic Other Firm")).toHaveCount(0);
  expect((await backend(page, `/auditor/engagements/${OTHER_ENGAGEMENT}/pipeline-stage`, "PATCH", { stage: "auditor_review" })).status).toBe(404);
});

test("client cannot read pipeline", async ({ page }) => {
  await signIn(page, "client");
  expect((await backend(page, "/auditor/pipeline")).status).toBe(403);
});
