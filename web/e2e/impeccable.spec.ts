import { expect, test } from "@playwright/test";

for (const role of ["client", "auditor"] as const) {
  test(`${role} long firm heading remains readable at narrow and zoom-sized widths`, async ({ page }) => {
    await page.addInitScript((role) => localStorage.setItem("ains-synthetic-role", role), role);
    for (const width of [1440, 768, 390]) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(role === "auditor" ? "/auditor" : "/");
      const title = page.locator("[data-page-header] h1");
      await expect(title).toBeVisible();
      // Stress the existing variable-content role without persisting a firm edit.
      await title.evaluate((element) => {
        element.textContent = `SyntheticFirm${"LongIdentifier".repeat(35)}`;
      });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      expect(await title.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
    }
  });
}

test("long report prose remains readable in the phone print view", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("ains-synthetic-role", "auditor"));
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/auditor/reports");
  await page.getByRole("button", { name: "Draft report", exact: true }).first().click();
  const text = `SyntheticReference${"LongUnbrokenIdentifier".repeat(40)}`;
  await page.getByRole("textbox", { name: "Scope", exact: true }).fill(text);
  await page.getByRole("button", { name: "Save draft", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "Draft saved." })).toBeVisible();
  await page.getByRole("link", { name: "Print view", exact: true }).click();
  const prose = page.locator(".report-rich").filter({ hasText: text }).first();
  await expect(prose).toContainText(text);
  expect(await prose.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
