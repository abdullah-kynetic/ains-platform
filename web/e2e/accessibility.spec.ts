import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("theme toggle persists light and dark mode", async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => {
    localStorage.setItem("ains-theme", "light");
    document.documentElement.classList.remove("dark");
  });

  await page.getByRole("button", { name: "Dark theme", exact: true }).click();
  await expect(page.locator("html")).toHaveClass(/dark/);
  expect(await page.evaluate(() => localStorage.getItem("ains-theme"))).toBe(
    "dark",
  );

  await page.getByRole("button", { name: "Light theme", exact: true }).click();
  await expect(page.locator("html")).not.toHaveClass(/dark/);
  expect(await page.evaluate(() => localStorage.getItem("ains-theme"))).toBe(
    "light",
  );
});

test("client and auditor screens meet automated accessibility basics", async ({
  page,
}) => {
  test.setTimeout(90000);
  for (const path of ["/", "/checklist", "/upload", "/questionnaire"]) {
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    const result = await new AxeBuilder({ page })
      .exclude("nextjs-portal")
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(
      result.violations,
      `${path}: ${JSON.stringify(result.violations)}`,
    ).toEqual([]);
    if (path === "/upload")
      await page.screenshot({
        path: "test-results/upload-desktop.png",
        fullPage: true,
      });
  }
  await page.evaluate(() =>
    localStorage.setItem("ains-synthetic-role", "auditor"),
  );
  await page.goto("/auditor");
  await expect(
    page.getByRole("heading", { name: "Today", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Latest activity" }),
  ).toBeVisible();
  await expect(page.getByText("Internal only", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Upcoming tasks" }),
  ).toBeVisible();
  const firstTask = page.getByRole("checkbox", {
    name: "Mark Review newly uploaded program evidence complete",
  });
  await firstTask.check();
  await expect(firstTask).toBeChecked();
  expect(
    (
      await new AxeBuilder({ page })
        .exclude("nextjs-portal")
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page.getByRole("link", { name: "Open audit workspace" }).click();
  await expect(
    page.getByRole("heading", { name: "Report readiness" }),
  ).toBeVisible();
  await page.locator("summary").filter({ hasText: "AML-BD-001:" }).click();
  expect(
    (
      await new AxeBuilder({ page })
        .exclude("nextjs-portal")
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
});

test("mobile navigation traps focus, closes with Escape and avoids horizontal overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/upload");
  await expect(
    page.getByRole("heading", { name: "Upload center" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Open menu" }).click();
  const dialog = page.getByRole("dialog", { name: "Navigation" });
  await expect(dialog).toBeVisible();
  await page.keyboard.press("Shift+Tab");
  expect(
    await dialog.evaluate((node) => node.contains(document.activeElement)),
  ).toBe(true);
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await expect(page.getByRole("button", { name: "Open menu" })).toBeFocused();
  const overflowing = await page
    .locator("body *")
    .evaluateAll((nodes) =>
      nodes
        .filter(
          (node) => node.getBoundingClientRect().right > window.innerWidth + 1,
        )
        .map((node) => `${node.tagName}.${node.className}`),
    );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
    JSON.stringify(overflowing),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/upload-mobile.png",
    fullPage: true,
  });
  await page.getByLabel("Select synthetic files").setInputFiles({
    name: `${"synthetic-".repeat(12)}.txt`,
    mimeType: "text/plain",
    buffer: Buffer.from("Synthetic mobile fixture"),
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  for (const path of ["/", "/checklist", "/questionnaire"]) {
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
      path,
    ).toBe(true);
  }
  await page.getByRole("button", { name: "Open menu" }).click();
  await page.evaluate(() =>
    localStorage.setItem("ains-synthetic-role", "auditor"),
  );
  await page.goto("/auditor");
  await page.getByRole("link", { name: "Open audit workspace" }).click();
  await page.locator("summary").filter({ hasText: "AML-BD-001:" }).click();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("load failure can be retried and empty requests have an explanation", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page.evaluate(() =>
    localStorage.setItem(
      "ains-synthetic-engagement-v1",
      "invalid synthetic metadata",
    ),
  );
  await page.goto("/checklist");
  await expect(page.getByText("We couldn’t load this screen.")).toBeVisible();
  await page.evaluate(() =>
    localStorage.removeItem("ains-synthetic-engagement-v1"),
  );
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(
    page.getByRole("heading", { name: "Document checklist" }),
  ).toBeVisible();
  await page
    .getByLabel("Search document requests")
    .fill("no-such-synthetic-request");
  await expect(
    page.getByText("No matching requests", { exact: true }),
  ).toBeVisible();
});


test("system theme follows OS changes, persists, and client firm card is static", async ({
  page,
}) => {
  await page.emulateMedia({ colorScheme: "light" });
  await page.goto("/upload");
  const sidebar = page.locator(".desktop-sidebar");
  await expect(
    sidebar.getByRole("button", { name: /Example Securities/ }),
  ).toHaveCount(0);
  await expect(
    sidebar.getByRole("link", { name: "Add client workspace" }),
  ).toHaveCount(0);
  await expect(page.getByText("Your engagement", { exact: true })).toHaveCount(
    0,
  );
  await sidebar
    .getByRole("button", { name: "System theme", exact: true })
    .click();
  await expect(
    sidebar.getByRole("button", { name: "System theme", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.emulateMedia({ colorScheme: "dark" });
  await expect(page.locator("html")).toHaveClass(/dark/);
  await expect(
    sidebar.getByRole("link", { name: "Upload", exact: true }),
  ).toHaveAttribute("aria-current", "page");
  await page.reload();
  await expect(page.locator("html")).toHaveClass(/dark/);
  await page.emulateMedia({ colorScheme: "light" });
  await expect(page.locator("html")).not.toHaveClass(/dark/);
  expect(await page.evaluate(() => localStorage.getItem("ains-theme"))).toBe(
    "system",
  );
  await sidebar
    .getByRole("button", { name: "Dark theme", exact: true })
    .click();
  await page.emulateMedia({ colorScheme: "light" });
  await expect(page.locator("html")).toHaveClass(/dark/);
});

test("theme reveal animates effective changes from segment and System origins", async ({
  page,
}) => {
  await page.emulateMedia({
    colorScheme: "light",
    reducedMotion: "no-preference",
  });
  await page.addInitScript(() => {
    localStorage.setItem("ains-theme", "light");
    const start = document.startViewTransition.bind(document);
    const calls: { x: string; y: string }[] = [];
    Object.assign(window, { themeTransitions: calls });
    document.startViewTransition = (callback) => {
      calls.push({
        x: document.documentElement.style.getPropertyValue(
          "--theme-transition-x",
        ),
        y: document.documentElement.style.getPropertyValue(
          "--theme-transition-y",
        ),
      });
      return start(callback);
    };
  });
  await page.goto("/");
  const sidebar = page.locator(".desktop-sidebar");
  const dark = sidebar.getByRole("button", { name: "Dark theme", exact: true });
  const light = sidebar.getByRole("button", {
    name: "Light theme",
    exact: true,
  });
  const system = sidebar.getByRole("button", {
    name: "System theme",
    exact: true,
  });
  const calls = () =>
    page.evaluate(
      () =>
        (
          window as unknown as {
            themeTransitions: { x: string; y: string }[];
          }
        ).themeTransitions,
    );
  const settled = () =>
    expect
      .poll(() =>
        page.evaluate(() =>
          document.documentElement.style.getPropertyValue(
            "--theme-transition-x",
          ),
        ),
      )
      .toBe("");
  await dark.click({ position: { x: 8, y: 8 } });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  const bounds = await dark.boundingBox();
  expect((await calls())[0]).toEqual({
    x: `${Math.floor(bounds!.x + 8)}px`,
    y: `${Math.floor(bounds!.y + 8)}px`,
  });
  await settled();
  await dark.click();
  expect(await calls()).toHaveLength(1);
  await light.focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  const lightBounds = await light.boundingBox();
  expect((await calls())[1]).toEqual({
    x: `${lightBounds!.x + lightBounds!.width / 2}px`,
    y: `${lightBounds!.y + lightBounds!.height / 2}px`,
  });
  await settled();
  await system.click();
  expect(await calls()).toHaveLength(2);
  await dark.click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await settled();
  await system.click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  expect(await calls()).toHaveLength(4);
  await settled();
  await page.emulateMedia({ colorScheme: "dark" });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  const systemBounds = await system.boundingBox();
  expect((await calls())[4]).toEqual({
    x: `${systemBounds!.x + systemBounds!.width / 2}px`,
    y: `${systemBounds!.y + systemBounds!.height / 2}px`,
  });
  await settled();
  await sidebar.evaluate((element) => {
    (element as HTMLElement).style.display = "none";
  });
  await page.emulateMedia({ colorScheme: "light" });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  expect((await calls())[5]).toEqual(
    await page.evaluate(() => ({
      x: `${window.innerWidth / 2}px`,
      y: `${window.innerHeight / 2}px`,
    })),
  );
  await settled();
  await sidebar.evaluate((element) => {
    (element as HTMLElement).style.display = "";
  });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await dark.click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  expect(await calls()).toHaveLength(6);
  expect(
    await sidebar.locator(".theme-indicator").evaluate(
      (element) => getComputedStyle(element).transitionProperty,
    ),
  ).toBe("none");
});
