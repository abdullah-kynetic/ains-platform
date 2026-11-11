import { test, expect } from "./fixtures";

/** Synthetic (mock build) coverage of the demo workflow screens; the real-backend journey is web/e2e-live/demo-journey-live.spec.ts. */
const ENG = "eng-synthetic-001";

async function asRole(page: import("@playwright/test").Page, role: "auditor" | "client") {
  await page.goto("/");
  await page.evaluate((r) => localStorage.setItem("ains-synthetic-role", r), role);
}

test("step 2: auditor sends the checklist and the client sees it was sent", async ({ page }) => {
  await asRole(page, "client");
  await page.goto("/");
  await expect(page.getByTestId("checklist-status")).toContainText("has not sent the checklist yet");

  await asRole(page, "auditor");
  await page.goto(`/auditor/engagements/${ENG}`);
  const card = page.getByTestId("client-checklist-card");
  await expect(card.getByTestId("workflow-stage")).toHaveText("Checklist not sent");
  await card.getByRole("button", { name: "Send checklist to client" }).click();
  await expect(card.getByTestId("workflow-stage")).toHaveText("Checklist sent");
  await expect(card.getByRole("button", { name: "Send checklist to client" })).toHaveCount(0);

  await asRole(page, "client");
  await page.goto("/checklist");
  await expect(page.getByTestId("checklist-status")).toContainText("Your auditor sent the checklist");
});
