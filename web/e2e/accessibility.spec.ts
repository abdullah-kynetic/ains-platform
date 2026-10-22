import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("theme toggle persists light and dark mode", async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => {
    localStorage.setItem("ains-theme", "light");
    document.documentElement.classList.remove("dark");
  });

  await page.getByRole("button", { name: "Toggle color theme" }).click();
  await expect(page.locator("html")).toHaveClass(/dark/);
  expect(await page.evaluate(() => localStorage.getItem("ains-theme"))).toBe(
    "dark",
  );

  await page.getByRole("button", { name: "Toggle color theme" }).click();
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
  await page.getByRole("button", { name: /Example Securities LLC/ }).click();
  await page.getByRole("button", { name: /AINS Operations/ }).click();
  await expect(
    page.getByRole("heading", { name: "Client audits" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Latest activity" }),
  ).toBeVisible();
  await expect(page.getByText("Internal only", { exact: true })).toBeVisible();
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
  await page.locator("summary").filter({ hasText: "AML-BD-001 —" }).click();
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
  await page.getByLabel("Request", { exact: true }).selectOption("AML-BD-001");
  await page
    .getByLabel("Select synthetic files")
    .setInputFiles({
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
  await page.getByRole("button", { name: /Example Securities LLC/ }).click();
  await page.getByRole("button", { name: /AINS Operations/ }).click();
  await page.getByRole("link", { name: "Open audit workspace" }).click();
  await page.locator("summary").filter({ hasText: "AML-BD-001 —" }).click();
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

test("sign-in form has accessible labels and a useful failed-sign-in state", async ({
  page,
}) => {
  await page.addInitScript(() =>
    localStorage.setItem("ains-synthetic-signed-out", "true"),
  );
  await page.goto("/sign-in");
  await expect(
    page.getByRole("heading", { name: "Sign in to AINS" }),
  ).toBeVisible();
  expect(
    (
      await new AxeBuilder({ page })
        .exclude("nextjs-portal")
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page
    .getByLabel("Email", { exact: true })
    .fill("synthetic@example.invalid");
  await page
    .getByLabel("Password", { exact: true })
    .fill("synthetic-only-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page
      .getByRole("alert")
      .filter({ hasText: "Demo mode does not accept credentials" }),
  ).toBeVisible();
});
