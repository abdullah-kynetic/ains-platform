import { expect, test } from "@playwright/test";
for (const role of ["client", "auditor"] as const) {
  test(`${role} page actions and top navigation remain accessible`, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.addInitScript(value => localStorage.setItem("ains-synthetic-role", value), role);
    await page.goto(role === "auditor" ? "/auditor" : "/");
    const header = page.locator("[data-page-header]").first();
    await expect(header.getByRole("button", { name: "Search workspace", exact: true })).toBeVisible();
    await expect(header.locator("a").first()).toBeVisible();
    const nav = page.getByRole("navigation", { name: "Main navigation" });
    await expect(nav.getByRole("link", { name: "Overview", exact: true })).toHaveAttribute("aria-current", "page");
    const bar = page.locator(".workspace-topbar");
    for (const theme of ["Light", "Dark", "System"]) {
      const button = bar.getByRole("button", { name: `${theme} theme`, exact: true });
      await button.click();
      await expect(button).toHaveAttribute("aria-pressed", "true");
    }
    await page.setViewportSize({ width: 375, height: 812 });
    await page.getByRole("button", { name: "Open menu" }).click();
    const drawer = page.getByRole("dialog", { name: "Navigation" });
    await expect(drawer.getByRole("group", { name: "Color theme" })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("button", { name: "Open menu" })).toBeFocused();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  });
}
