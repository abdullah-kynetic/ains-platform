import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
for (const role of ["client", "auditor"]) {
  test(`${role} onboarding completes once and stays dismissed`, async ({
    page,
  }) => {
    await page.addInitScript((role) => {
      localStorage.setItem("ains-synthetic-role", role);
      localStorage.setItem("kien-synthetic-onboarding-enabled", "1");
    }, role);
    await page.goto(role === "auditor" ? "/auditor" : "/");
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    expect(
      (
        await new AxeBuilder({ page })
          .exclude("nextjs-portal")
          .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
          .analyze()
      ).violations,
    ).toEqual([]);
    await expect(
      dialog.getByRole("group", { name: "Step 1 of 3" }),
    ).toBeVisible();
    await dialog.getByRole("button", { name: "Next", exact: true }).click();
    await dialog.getByRole("button", { name: "Next", exact: true }).click();
    await dialog
      .getByRole("button", { name: "Get started", exact: true })
      .click();
    await expect(dialog).toBeHidden();
    await page.reload();
    await expect(dialog).toBeHidden();
    await page.setViewportSize({ width: 390, height: 844 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  });
  test(`${role} skip persists across reload`, async ({ page }) => {
    await page.addInitScript((role) => {
      localStorage.setItem("ains-synthetic-role", role);
      localStorage.setItem("kien-synthetic-onboarding-enabled", "1");
    }, role);
    await page.goto(role === "auditor" ? "/auditor" : "/");
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await dialog
      .getByRole("button", { name: "Skip tour", exact: true })
      .click();
    await expect(dialog).toBeHidden();
    await page.reload();
    await expect(dialog).toBeHidden();
  });
}
