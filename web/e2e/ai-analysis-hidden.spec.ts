import { expect, test } from "./fixtures";

// The synthetic demo build has no AI backend, and the real API answers 404 while
// AI_ANALYSIS_ENABLED is false. In both cases the auditor never sees the AI panel or its button.
test("AI analysis panel and Run button are hidden when the feature is off", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("ains-synthetic-role", "auditor"));
  await page.goto("/auditor/engagements/eng-synthetic-001/findings");
  await expect(page.getByRole("heading", { name: "Findings" })).toBeVisible();
  await expect(page.getByTestId("ai-analysis")).toHaveCount(0);
  await expect(page.getByRole("button", { name: /run ai analysis/i })).toHaveCount(0);
});
