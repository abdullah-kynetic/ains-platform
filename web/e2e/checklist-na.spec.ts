import { test, expect, type Page } from "./fixtures";

/** The client can ask for N/A only after the auditor has sent the checklist. */
async function sendChecklist(page: Page) {
  await page.goto("/");
  await page.evaluate(() => localStorage.setItem("ains-synthetic-role", "auditor"));
  await page.goto("/auditor/engagements/eng-synthetic-001");
  await page.getByRole("button", { name: "Send checklist to client" }).click();
  await expect(page.getByTestId("workflow-stage")).toHaveText("Checklist sent");
  await page.evaluate(() => localStorage.setItem("ains-synthetic-role", "client"));
}

test("auditor marks a request does-not-apply in the requests tab and can undo it", async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => localStorage.setItem("ains-synthetic-role", "auditor"));
  await page.goto("/auditor/engagements/eng-synthetic-001/requests");
  const request = page.locator("details").filter({has: page.locator("summary", {hasText: "AML-BD-001 —"})});
  await request.locator("summary").click();
  await request.getByRole("button", {name: "Does not apply", exact:true}).click();
  await expect(request.getByRole("button", {name: "Undo does not apply"})).toBeVisible();
  await expect(page.locator("details").filter({has: page.locator("summary", {hasText: /AML-BD-/})}).last()).toContainText("AML-BD-001");
  await request.getByRole("button", {name: "Undo does not apply"}).click();
  await expect(request.getByRole("button", {name: "Does not apply", exact:true})).toBeVisible();
});

test("client asks for N/A with a reason; the auditor approves it and it sorts last", async ({ page }) => {
  await sendChecklist(page);
  await page.goto("/checklist");
  const row = page.getByTestId("request-AML-BD-001");
  await row.getByRole("button", { name: "Does not apply: AML-BD-001" }).click();
  await row.getByLabel("Why does AML-BD-001 not apply to your firm?").fill("Synthetic reason: not relevant to this firm.");
  await row.getByRole("button", { name: "Send to auditor" }).click();
  await expect(row).toContainText("Waiting for your auditor");
  await page.reload();
  await expect(page.getByTestId("request-AML-BD-001")).toContainText("Waiting for your auditor");

  await page.evaluate(() => localStorage.setItem("ains-synthetic-role", "auditor"));
  await page.goto("/auditor/engagements/eng-synthetic-001/client-checklist");
  const decision = page.getByTestId("na-request-AML-BD-001");
  await expect(decision).toContainText("Synthetic reason: not relevant to this firm.");
  await decision.getByRole("button", { name: "Approve N/A" }).click();
  await expect(decision).toHaveCount(0);

  await page.evaluate(() => localStorage.setItem("ains-synthetic-role", "client"));
  await page.goto("/checklist");
  await expect(page.getByTestId("section-na")).toContainText("AML-BD-001");
  await expect(page.getByTestId("request-progress")).toContainText("1 of 34 requests");
});

test("auditor rejects an N/A request with a note the client can read", async ({ page }) => {
  await sendChecklist(page);
  await page.goto("/checklist");
  const row = page.getByTestId("request-AML-BD-002");
  await row.getByRole("button", { name: "Does not apply: AML-BD-002" }).click();
  await row.getByLabel("Why does AML-BD-002 not apply to your firm?").fill("Synthetic reason two.");
  await row.getByRole("button", { name: "Send to auditor" }).click();
  await page.evaluate(() => localStorage.setItem("ains-synthetic-role", "auditor"));
  await page.goto("/auditor/engagements/eng-synthetic-001/client-checklist");
  const decision = page.getByTestId("na-request-AML-BD-002");
  await expect(decision.getByRole("button", { name: "Reject" })).toBeDisabled();
  await decision.getByLabel("Note to the client (required to reject)").fill("Synthetic: please provide it.");
  await decision.getByRole("button", { name: "Reject" }).click();
  await page.evaluate(() => localStorage.setItem("ains-synthetic-role", "client"));
  await page.goto("/checklist");
  await expect(page.getByTestId("request-AML-BD-002")).toContainText("Your auditor needs this request: Synthetic: please provide it.");
});

test("client N/A request remains accessible on phone in dark mode", async ({ page }) => {
  await page.setViewportSize({width:390,height:844});
  await page.emulateMedia({reducedMotion:"reduce"});
  await sendChecklist(page);
  await page.goto("/checklist");
  await page.evaluate(() => localStorage.setItem("ains-theme","dark"));
  await page.reload();
  await page.getByRole("button",{name:"Does not apply: AML-BD-001",exact:true}).click();
  await expect(page.getByLabel("Why does AML-BD-001 not apply to your firm?")).toBeVisible();
  const { default: AxeBuilder } = await import("@axe-core/playwright");
  const result = await new AxeBuilder({page}).withTags(["wcag2a","wcag2aa","wcag21aa"]).analyze();
  expect(result.violations).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
