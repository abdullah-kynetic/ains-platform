import { expect, test } from "@playwright/test";

for (const role of ["client", "auditor"] as const) {
  test(`${role} inline header and pinned theme controls`, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.addInitScript(
      (role) => localStorage.setItem("ains-synthetic-role", role),
      role,
    );
    await page.goto(role === "auditor" ? "/auditor" : "/");
    const header = page.locator("[data-page-header]").first();
    const search = header.getByRole("button", {
      name: "Search workspace",
      exact: true,
    });
    const action = header.locator("a").first();
    await expect(search).toBeVisible();
    await expect(action).toBeVisible();
    await expect
      .poll(async () => {
        const s = await search.boundingBox(),
          a = await action.boundingBox();
        return (
          !!s &&
          !!a &&
          s.x + s.width <= a.x &&
          Math.abs(s.y + s.height / 2 - a.y - a.height / 2) < 3
        );
      })
      .toBe(true);
    const sidebar = page.locator(".desktop-sidebar");
    // Sidebar items may carry a count badge, so match the label as a prefix.
    const overview = sidebar.getByRole("link", {
      name: role === "auditor" ? /^Today/ : /^Overview/,
    });
    await expect(overview).toHaveAttribute("aria-current", "page");
    if (role === "auditor") {
      await page.goto("/");
      await expect(overview).toHaveAttribute("href", "/auditor");
      await expect(overview).toHaveAttribute("aria-current", "page");
    }
    for (const collapsed of [false, true]) {
      if (collapsed)
        await sidebar.getByRole("button", { name: "Collapse sidebar" }).click();
      await page.setViewportSize({ width: 1440, height: 420 });
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      for (const theme of ["Light", "Dark", "System"]) {
        const button = sidebar.getByRole("button", {
          name: `${theme} theme`,
          exact: true,
        });
        await expect(button).toBeInViewport({ ratio: 1 });
        await button.click();
        await expect(button).toHaveAttribute("aria-pressed", "true");
      }
      const control = sidebar.getByRole("group", { name: "Color theme" });
      const controlBounds = await control.boundingBox();
      const identity = sidebar.locator(".sidebar-identity");
      await expect(sidebar.locator(".sidebar-theme + .sidebar-identity")).toHaveCount(1);
      const identityBounds = await identity.boundingBox();
      const sidebarBounds = await sidebar.boundingBox();
      if (!collapsed) {
        expect(controlBounds!.y + controlBounds!.height).toBeLessThanOrEqual(identityBounds!.y);
      } else {
        await expect(identity).toBeHidden();
      }
      const bottomBounds = collapsed ? controlBounds! : identityBounds!;
      expect(
        sidebarBounds!.y + sidebarBounds!.height - bottomBounds.y - bottomBounds.height,
      ).toBeLessThanOrEqual(16);
      if (collapsed) {
        await expect(sidebar.locator(".theme-control svg").first()).toBeVisible();
        await expect(sidebar.locator(".theme-label").first()).toBeHidden();
      }
    }
    if (role === "auditor") {
      await sidebar.getByRole("link", { name: "Settings" }).click();
      await expect(overview).not.toHaveAttribute("aria-current", "page");
      await expect(
        sidebar.getByRole("link", { name: "Settings" }),
      ).toHaveAttribute("aria-current", "page");
    }
    await page.setViewportSize({ width: 375, height: 812 });
    await page.evaluate(() => window.scrollTo(0, 0));
    await expect(search).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.getByRole("button", { name: "Open menu" }).click();
    const drawer = page.getByRole("dialog");
    const control = drawer.getByRole("group", { name: "Color theme" });
    const identity = drawer.locator(".sidebar-identity");
    await expect(drawer.locator(".sidebar-theme + .sidebar-identity")).toHaveCount(1);
    await expect(control).toBeInViewport({ ratio: 1 });
    await expect(identity).toBeInViewport({ ratio: 1 });
    const controlBounds = await control.boundingBox();
    const identityBounds = await identity.boundingBox();
    const panelBounds = await drawer.locator(".sidebar-panel").boundingBox();
    expect(controlBounds!.y + controlBounds!.height).toBeLessThanOrEqual(identityBounds!.y);
    expect(
      panelBounds!.y + panelBounds!.height - identityBounds!.y - identityBounds!.height,
    ).toBeLessThanOrEqual(16);
  });
}
