import { expect, test } from "@playwright/test";

test("tile feedback, theme indicator and keyboard focus respect reduced motion", async ({ page }) => {
  await page.goto("/");
  const tile = page.getByRole("region", { name: "Quick actions" }).getByRole("link").first();
  await tile.hover();
  await expect(tile).toHaveCSS("transform", "matrix(1, 0, 0, 1, 0, -2)");
  await expect(tile.locator(".lucide-arrow-up-right")).toHaveCSS("transform", "matrix(1, 0, 0, 1, 2, -2)");
  await page.keyboard.press("Tab");
  await tile.focus();
  await expect(tile).toHaveCSS("outline-color", "rgb(184, 146, 74)");
  await expect(tile).toHaveCSS("outline-width", "2px");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await expect(tile).toHaveCSS("transform", "none");
  await expect(tile.locator(".lucide-arrow-up-right")).toHaveCSS("transform", "none");
  const themes = page.getByRole("group", { name: "Color theme" });
  for (const theme of ["Light", "Dark", "System"]) {
    const button = themes.getByRole("button", { name: theme + " theme", exact: true });
    await button.click();
    await expect(button).toHaveAttribute("aria-pressed", "true");
    expect(await themes.locator(".theme-indicator").evaluate((node) => parseFloat(getComputedStyle(node).transitionDuration))).toBeLessThan(0.001);
    const indicator = await themes.locator(".theme-indicator").boundingBox();
    const bounds = await button.boundingBox();
    expect(Math.abs(indicator!.x - bounds!.x)).toBeLessThan(1);
    await expect(page.locator(".sidebar-nav-active").first()).toHaveCSS("background-color", "color(srgb 0.721569 0.572549 0.290196 / 0.14)");
  }
  await expect(page.locator(".type-metric").first()).toHaveCSS("font-variant-numeric", "tabular-nums");
  await page.screenshot({ path: "test-results/apple-polish.png", fullPage: true });
});
