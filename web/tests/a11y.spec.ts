import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("client and auditor dashboards meet automated accessibility checks", async ({ page }) => {
  for (const [role, path] of [["client", "/"], ["auditor", "/auditor"]] as const) {
    await page.addInitScript((demoRole) => {
      localStorage.setItem("ains-synthetic-role", demoRole);
    }, role);
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    const results = await new AxeBuilder({ page })
      .exclude("nextjs-portal")
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(results.violations, `${path}: ${JSON.stringify(results.violations)}`).toEqual([]);
  }
});
