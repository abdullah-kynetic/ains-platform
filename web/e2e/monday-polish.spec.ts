import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
for (const role of ["client", "auditor"]) {
  test(`${role} theme controls and top bar on long pages`, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.addInitScript(value => localStorage.setItem("ains-synthetic-role", value), role);
    await page.goto(role === "client" ? "/checklist" : "/auditor/engagements");
    const topbar = page.locator(".workspace-topbar");
    await expect(topbar).toBeVisible();
    for (const theme of ["Dark", "Light", "System"]) {
      await topbar.getByRole("button", {name: `${theme} theme`, exact: true}).click();
      expect((await new AxeBuilder({page}).include(".workspace-topbar .theme-control").withRules(["color-contrast"]).analyze()).violations).toEqual([]);
    }
    await page.evaluate(() => scrollTo(0, document.body.scrollHeight));
    await expect(topbar).toBeInViewport();
  });
}
