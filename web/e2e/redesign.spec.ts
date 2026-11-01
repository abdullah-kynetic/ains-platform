import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

async function axe(page: import("@playwright/test").Page) {
  await page.evaluate(async () => { await Promise.allSettled(document.getAnimations().map(animation => animation.finished)); });
  expect(
    (await new AxeBuilder({ page }).exclude("nextjs-portal").analyze())
      .violations,
  ).toEqual([]);
}
test("auditor overview, sidebar rail and desktop screenshot", async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.addInitScript(() =>
    localStorage.setItem("ains-synthetic-role", "auditor"),
  );
  await page.goto("/auditor");
  await expect(
    page.getByRole("heading", { name: "Today", exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("region", { name: "Today at a glance" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Still to review", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Needs you today", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Upcoming deadlines", exact: true })).toBeVisible();
  await axe(page);
  await page.screenshot({
    path: testInfo.outputPath("auditor-overview.png"),
    style: "nextjs-portal { display: none; }",
  });
  await page.getByRole("button", { name: "Collapse sidebar" }).click();
  await expect(
    page.getByRole("button", { name: "Expand sidebar" }),
  ).toHaveAttribute("aria-expanded", "false");
  await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("link", { name: "Settings" })
    .click();
  await expect(page).toHaveURL(/\/auditor\/settings/, { timeout: 30000 });
  await expect(
    page.getByRole("heading", { name: "Settings", exact: true }),
  ).toBeVisible({ timeout: 30000 });
  await page.getByRole("button", { name: "Expand sidebar" }).click();
  await page.getByLabel("Display name").fill("Synthetic Reviewer");
  await page.getByLabel("Weekly engagement digest").uncheck();
  await page.getByRole("button", { name: "Save preview preferences" }).click();
  await expect(page.getByRole("status")).toContainText(
    "Preview preferences saved",
  );
  await axe(page);
  await page.keyboard.press("Meta+k");
  await page.getByRole("textbox", { name: "Search pages" }).fill("dark");
  await page.keyboard.press("ArrowDown");
  await expect(
    page.getByRole("dialog").getByRole("button", { name: "Dark theme", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("html")).toHaveClass(/dark/);
  await axe(page);
});

test("engagement table searches, filters, sorts and paginates assigned records", async ({
  page,
}) => {
  await page.addInitScript(() => {
    localStorage.setItem("ains-synthetic-role", "auditor");
    localStorage.setItem(
      "ains-synthetic-workspaces-v1",
      JSON.stringify(
        Array.from({ length: 7 }, (_, i) => ({
          id: `synthetic-${i}`,
          firmId: `firm-${i}`,
          firmName: `Synthetic Firm ${i}`,
          slug: `synthetic-${i}`,
          status: "draft",
          requestCount: 34,
          clientAccessProvisioned: false,
        })),
      ),
    );
  });
  await page.goto("/auditor/engagements");
  await expect(page.getByRole("status")).toContainText(
    "8 results · Page 1 of 2",
  );
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Page 2 of 2");
  await page.getByRole("button", { name: "Firm", exact: true }).click();
  await expect(
    page.getByRole("columnheader", { name: "Firm", exact: true }),
  ).toHaveAttribute("aria-sort", "descending");
  await page
    .getByRole("combobox", { name: "Rows per page" })
    .selectOption("10");
  await expect(page.getByRole("status")).toContainText("Page 1 of 1");
  await page
    .getByRole("textbox", { name: "Search engagements" })
    .fill("Firm 3");
  await expect(
    page.getByRole("cell", { name: /Synthetic Firm 3/ }),
  ).toBeVisible();
  await expect(page.getByRole("status")).toContainText("1 results");
  await page
    .getByRole("combobox", { name: "Filter engagement status" })
    .selectOption("ready");
  await expect(
    page.getByText("No engagements match these filters."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Clear filters" }).click();
  await page
    .getByRole("textbox", { name: "Search engagements" })
    .fill("Example Securities");
  await page.getByRole("button", { name: "View engagement details" }).click();
  const drawer = page.getByRole("dialog", { name: "Engagement details" });
  await expect(
    drawer.getByRole("heading", { name: "Recent audit entries" }),
  ).toBeVisible();
  await expect(drawer.locator("time").first()).toBeVisible();
  await axe(page);
});

test("client home uses sidebar navigation, messages and desktop screenshot; auditor routes remain gated", async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await expect(page.getByRole("region", { name: "Quick actions" })).toHaveCount(0);
  await expect(page.locator("aside.desktop-sidebar").getByRole("link", { name: "Upload", exact: true })).toBeVisible();
  await axe(page);
  await page.screenshot({ path: testInfo.outputPath("client-home.png") });
  await page.getByRole("navigation", { name: "Main navigation" }).getByRole("link", { name: "Messages", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Messages" })).toBeVisible();
  await axe(page);
  for (const route of ["/auditor/settings", "/auditor/engagements"]) {
    await page.goto(route);
    await expect(page).toHaveURL(/\/$/);
    await expect(
      page.getByRole("heading", { name: "Settings", exact: true }),
    ).toHaveCount(0);
  }
});

test("client sidebar lists every route and supports collapse, mobile navigation and sign out", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  const sidebar = page.locator(".desktop-sidebar");
  const links = sidebar.getByRole("navigation", { name: "Main navigation" }).getByRole("link");
  await expect(links).toHaveText([/^Overview/, /^Upload/, /^Checklist/, /^Questionnaire/, /^Messages/, /^Progress/, /^Responses requested/, /^Report/, /^Invoices/]);
  const routes = ["/", "/upload", "/checklist", "/questionnaire", "/messages", "/progress"];
  for (let i = 0; i < routes.length; i++) {
    await expect(links.nth(i)).toHaveAttribute("href", routes[i]);
    await links.nth(i).click();
    await expect(links.nth(i)).toHaveAttribute("aria-current", "page");
  }
  await expect(sidebar.getByTitle("Example Securities LLC", { exact: true })).toBeVisible();
  await expect(sidebar.getByText("Client workspace · Synthetic")).toHaveCount(0);
  await sidebar.getByRole("button", { name: "Collapse sidebar" }).click();
  const expand = sidebar.getByRole("button", { name: "Expand sidebar" });
  await expect(expand).toBeVisible();
  await expand.focus();
  await page.keyboard.press("Enter");
  await expect(sidebar.getByRole("button", { name: "Collapse sidebar" })).toHaveAttribute("aria-expanded", "true");
  await page.setViewportSize({ width: 375, height: 812 });
  await page.getByRole("button", { name: "Open menu" }).click();
  const sheet = page.getByRole("dialog", { name: "Navigation" });
  await expect(sheet.getByRole("navigation").getByRole("link")).toHaveText([/^Overview/, /^Upload/, /^Checklist/, /^Questionnaire/, /^Messages/, /^Progress/, /^Responses requested/, /^Report/, /^Invoices/]);
  await sheet.getByRole("link", { name: "Messages", exact: true }).click();
  await expect(page).toHaveURL(/\/messages$/);
  await expect(sheet).not.toBeVisible();
});
