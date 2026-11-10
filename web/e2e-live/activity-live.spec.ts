import { expect, test } from "@playwright/test";
import { backend, ownEngagement, signIn } from "./helpers";

test("engagement activity uses the real assigned-auditor feed", async ({ page }) => {
  await signIn(page);
  const id = await ownEngagement(page);
  await page.goto(`/auditor/engagements/${id}/activity`);
  await expect(page.getByText(/uploaded new evidence for/)).toBeVisible();
  await expect(page.getByRole("listitem").filter({ hasText: "uploaded new evidence for" })).toContainText("Synthetic E2E Client");
  await expect(page.getByText("Synthetic Other Firm")).toHaveCount(0);
  await expect(page.getByTestId("mock-notice")).toHaveCount(0);
});

test("client cannot read auditor activity", async ({ page }) => {
  await signIn(page, "client");
  expect((await backend(page, "/auditor/activity")).status).toBe(403);
});
