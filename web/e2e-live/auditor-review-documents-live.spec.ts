import { expect, test } from "@playwright/test";
import { backend, OTHER_ENGAGEMENT, ownEngagement, signIn } from "./helpers";

test("assigned auditor sees stored document receipts after reload; foreign workspace is denied", async ({ page }) => {
  await signIn(page);
  const id = await ownEngagement(page);
  await page.goto(`/auditor/engagements/${id}/documents`);
  const row = page.getByRole("row").filter({ hasText: "synthetic-review-policy.pdf" });
  await expect(row).toContainText("AML-BD-001");
  await expect(row).toContainText("Received");
  await expect(page.getByTestId("mock-notice")).toHaveCount(0);
  await page.reload();
  await expect(row).toBeVisible();
  expect((await backend(page, `/auditor/engagements/${OTHER_ENGAGEMENT}/workspace`)).status).toBe(404);
  await page.goto(`/auditor/engagements/${OTHER_ENGAGEMENT}/documents`);
  await expect(page.getByText("synthetic-review-policy.pdf")).toHaveCount(0);
  await expect(page.getByRole("button", { name: /try again|retry/i })).toBeVisible();
});

test("client cannot read auditor document workspace", async ({ page }) => {
  await signIn(page, "client");
  expect((await backend(page, `/auditor/engagements/${OTHER_ENGAGEMENT}/workspace`)).status).toBe(403);
});
