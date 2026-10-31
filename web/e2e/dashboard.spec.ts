import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("command palette supports shortcuts, filtering, navigation and focus return", async ({ page }) => {
  await page.goto("/");
  const trigger = page.getByRole("button", { name: "Search workspace", exact: true });
  await trigger.click();
  const palette = page.getByRole("dialog", { name: "Go to workspace" });
  await expect(palette).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Search pages" })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(trigger).toBeFocused();
  await page.keyboard.press("Meta+k");
  await page.getByRole("textbox", { name: "Search pages" }).fill("no matching page");
  await expect(palette.getByText("No pages match.", { exact: false })).toBeVisible();
  await page.getByRole("textbox", { name: "Search pages" }).fill("questionnaire");
  expect((await new AxeBuilder({ page }).exclude("nextjs-portal").analyze()).violations).toEqual([]);
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/questionnaire$/);
  await expect(palette).not.toBeVisible();
  await page.keyboard.press("Control+k");
  await expect(palette).toBeVisible();
  await expect(palette.getByRole("button", { name: "Audit pipeline" })).toHaveCount(0);
});

test("engagement drawer contains a timeline, traps focus and keeps full workspace available", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("ains-synthetic-role", "auditor"));
  await page.goto("/auditor");
  const trigger = page.getByRole("button", { name: "View engagement details" }).first();
  await trigger.click();
  const drawer = page.getByRole("dialog", { name: "Engagement details" });
  await expect(drawer.getByRole("heading", { name: "Activity timeline" })).toBeVisible();
  await expect(drawer.locator("time").first()).toBeVisible();
  await page.keyboard.press("Shift+Tab");
  expect(await drawer.evaluate((node) => node.contains(document.activeElement))).toBe(true);
  expect((await new AxeBuilder({ page }).exclude("nextjs-portal").analyze()).violations).toEqual([]);
  await page.keyboard.press("Escape");
  await expect(trigger).toBeFocused();
  await page.setViewportSize({ width: 375, height: 812 });
  await trigger.click();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await drawer.getByRole("link", { name: "Continue to audit workspace" }).click();
  await expect(page.getByRole("heading", { name: "Report readiness" })).toBeVisible();
});

test("client dashboard uses sidebar navigation and neutral intake state", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle("Kynetic portal");
  const footer = page.getByRole("contentinfo");
  await expect(footer).toContainText("Kien by Kien Solutions");
  await expect(footer.getByRole("link", { name: "kiensolutions.com" })).toHaveAttribute(
    "href",
    "https://kiensolutions.com",
  );
  await expect(page.getByText("Synthetic demonstration workspace")).toBeVisible();
  await expect(page.getByRole("region", { name: "Quick actions" })).toHaveCount(0);
  await expect(page.getByRole("table")).toHaveCount(0);
  await expect(page.getByText("Internal finding drafts")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "View engagement details" })).toHaveCount(0);
  await page.getByRole("navigation", { name: "Main navigation" }).getByRole("link", { name: "Upload", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Upload center" })).toBeVisible();
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  expect((await new AxeBuilder({ page }).exclude("nextjs-portal").analyze()).violations).toEqual([]);
  await page.getByRole("button", { name: "Search workspace", exact: true }).click();
  await expect(page.getByRole("dialog", { name: "Go to workspace" })).toBeVisible();
});
