import { expect, test } from "@playwright/test";

test("tile feedback, theme indicator and keyboard focus respect reduced motion", async ({
  page,
}) => {
  await page.goto("/");
  const tile = page
    .getByRole("region", { name: "Quick actions" })
    .getByRole("link")
    .first();
  await tile.hover();
  await expect(tile).toHaveCSS("transform", "matrix(1, 0, 0, 1, 0, -2)");
  await expect(tile.locator(".lucide-arrow-up-right")).toHaveCSS(
    "transform",
    "matrix(1, 0, 0, 1, 2, -2)",
  );
  await page.keyboard.press("Tab");
  await tile.focus();
  await expect(tile).toHaveCSS("outline-color", "rgb(184, 146, 74)");
  await expect(tile).toHaveCSS("outline-width", "2px");
  await page.emulateMedia({ reducedMotion: "reduce" });
  await expect(tile).toHaveCSS("transform", "none");
  await expect(tile.locator(".lucide-arrow-up-right")).toHaveCSS(
    "transform",
    "none",
  );
  const themes = page.getByRole("group", { name: "Color theme" });
  for (const theme of ["Light", "Dark", "System"]) {
    const button = themes.getByRole("button", {
      name: theme + " theme",
      exact: true,
    });
    await button.click();
    await expect(button).toHaveAttribute("aria-pressed", "true");
    expect(
      await themes
        .locator(".theme-indicator")
        .evaluate((node) =>
          parseFloat(getComputedStyle(node).transitionDuration),
        ),
    ).toBeLessThan(0.001);
    const indicator = await themes.locator(".theme-indicator").boundingBox();
    const bounds = await button.boundingBox();
    expect(Math.abs(indicator!.x - bounds!.x)).toBeLessThan(1);
    await expect(page.locator(".sidebar-nav-active").first()).toHaveCSS(
      "background-color",
      "color(srgb 0.721569 0.572549 0.290196 / 0.14)",
    );
  }
  await expect(page.locator(".type-metric").first()).toHaveCSS(
    "font-variant-numeric",
    "tabular-nums",
  );
  await page.screenshot({
    path: "test-results/apple-polish.png",
    fullPage: true,
  });
});

test("header search shares the action row and remains available without a page action", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  const search = page.getByRole("button", {
    name: "Search workspace",
    exact: true,
  });
  const checklist = page.getByRole("link", {
    name: "Open checklist",
    exact: true,
  });
  await expect(search).toBeVisible();
  const searchBounds = await search.boundingBox();
  const actionBounds = await checklist.boundingBox();
  expect(Math.abs(searchBounds!.y - actionBounds!.y)).toBeLessThan(1);
  await page.goto("/messages");
  await expect(search).toBeVisible();
  await search.click();
  await expect(
    page.getByRole("dialog", { name: "Go to workspace" }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(search).toBeFocused();
});

test("collapsed appearance controls stay visible and auditor overview is active", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.addInitScript(() =>
    localStorage.setItem("ains-synthetic-role", "auditor"),
  );
  await page.goto("/auditor");
  const sidebar = page.locator(".desktop-sidebar");
  await expect(
    sidebar.getByRole("link", { name: "Overview", exact: true }),
  ).toHaveAttribute("aria-current", "page");
  await expect(
    sidebar.getByRole("link", { name: "Engagements", exact: true }),
  ).not.toHaveAttribute("aria-current", "page");
  // The development tools launcher otherwise covers the bottom icon in the rail.
  await page.addStyleTag({ content: "nextjs-portal { display: none; }" });
  await sidebar.getByRole("button", { name: "Collapse sidebar" }).click();
  for (const theme of ["Dark", "Light", "System"]) {
    const button = sidebar.getByRole("button", {
      name: `${theme} theme`,
      exact: true,
    });
    await expect(button).toBeVisible();
    await expect(button.locator("svg")).toBeVisible();
    await expect(button.locator(".theme-label")).toBeHidden();
    await button.click();
    await expect(button).toHaveAttribute("aria-pressed", "true");
    const box = await button.boundingBox();
    expect(box!.y + box!.height).toBeLessThanOrEqual(900);
    expect(box!.height).toBeGreaterThanOrEqual(44);
  }
});

test("progress, loading and floating materials honor accessibility preferences", async ({
  page,
}) => {
  await page.goto("/checklist");
  const progress = page.getByRole("progressbar").first();
  await expect(progress).toBeVisible();
  const fill = progress.locator(".progress-fill");
  expect(
    await fill.evaluate((node) =>
      parseFloat(getComputedStyle(node).borderRadius),
    ),
  ).toBeGreaterThan(8);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await expect(fill).toHaveCSS("transition-duration", "0s");
  await expect(page.locator(".page-enter").first()).toHaveCSS(
    "animation-name",
    "none",
  );
  await page
    .getByRole("button", { name: "Search workspace", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByRole("dialog")).toHaveCSS("backdrop-filter", "none");
});
