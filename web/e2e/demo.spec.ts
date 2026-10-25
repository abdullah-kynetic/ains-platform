import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("synthetic document progress uses the current catalog without backend calls", async ({ page }) => {
  const backendCalls: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes(":8000")) backendCalls.push(request.url());
  });
  await page.goto("/");
  await expect(page.getByText("Synthetic demonstration workspace")).toBeVisible();
  await page.getByRole("link", { name: "Progress", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Your document progress" })).toBeVisible();
  await expect(page.getByText("Document acceptance is not an audit conclusion.", { exact: false })).toBeVisible();
  await expect(page.getByRole("progressbar").first()).toBeVisible();
  expect((await new AxeBuilder({ page }).exclude("nextjs-portal").withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze()).violations).toEqual([]);
  await page.getByRole("link", { name: "Upload documents", exact: true }).click();
  await expect(page).toHaveURL(/\/checklist$/);
  expect(backendCalls).toEqual([]);
});
