import { test, expect } from "./fixtures";
import AxeBuilder from "@axe-core/playwright";
for (const role of ["client", "auditor"]) {
  test(`${role} theme contrast and sidebar fill on long pages`, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.addInitScript(role => localStorage.setItem("ains-synthetic-role", role), role);
    await page.goto(role === "client" ? "/checklist" : "/auditor/engagements");
    const sidebar = page.locator(".desktop-sidebar");
    await expect(sidebar).toBeVisible();
    for (const theme of ["Dark", "Light", "System"]) {
      await sidebar.getByRole("button", {name: `${theme} theme`, exact: true}).click();
      expect((await new AxeBuilder({page}).include(".theme-control").withRules(["color-contrast"]).analyze()).violations).toEqual([]);
    }
    for (const position of [0, 99999]) {
      await page.evaluate(y => scrollTo(0,y), position);
      const bounds = await sidebar.boundingBox();
      expect(Math.abs(bounds!.y)).toBeLessThanOrEqual(1);
      expect(bounds!.height).toBeGreaterThanOrEqual(900);
    }
  });
}
