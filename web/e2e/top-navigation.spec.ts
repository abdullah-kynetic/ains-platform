import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

for (const role of ["client", "auditor"] as const) {
  test(`${role} can navigate with the top bar and mobile menu`, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.addInitScript((value) => localStorage.setItem("ains-synthetic-role", value), role);
    await page.goto(role === "client" ? "/" : "/auditor");
    const navigation = page.getByRole("navigation", { name: "Main navigation" });
    await expect(navigation).toBeVisible();
    await expect(navigation.getByRole("link", { name: "Overview" })).toHaveAttribute("aria-current", "page");
    const profile = page.locator('summary[aria-label^="Profile and settings"]');
    await profile.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
    if (role === "auditor") await expect(page.getByRole("link", { name: "Settings", exact: true })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(profile).toBeFocused();
    await expect(page.getByRole("button", { name: "Sign out" })).not.toBeVisible();
    expect((await new AxeBuilder({ page }).exclude("nextjs-portal").withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze()).violations).toEqual([]);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.getByRole("button", { name: "Open menu" }).click();
    await expect(page.getByRole("dialog", { name: "Navigation" })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("button", { name: "Open menu" })).toBeFocused();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  });
}
