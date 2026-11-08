import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

function serverOrigin(host: string): string {
  const base = new URL(
    test.info().project.use.baseURL ?? "http://kynetic.localhost:3100",
  );
  return `${base.protocol}//${host}${base.port ? `:${base.port}` : ""}`;
}

async function expectUnknownFirm(page: Page, reason: "apex" | "www" | "missing") {
  const main = page.locator("main#main-content");
  await expect(main).toHaveAttribute("data-tenant-state", "unknown");
  await expect(main).toHaveAttribute("data-tenant-reason", reason);
  await expect(page.getByRole("heading", { name: "Unknown firm" })).toBeVisible();
  await expect(page.locator("html")).not.toHaveAttribute("data-firm-slug", /.+/);
  await expect(page.getByRole("heading", { name: "Sign in to Kien", exact: true })).toHaveCount(0);
}

test("tenant host exposes the firm slug and mock branding", async ({ page }, testInfo) => {
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("data-firm-slug", "kynetic");
  await expect(page.getByText("Kynetic", { exact: true }).first()).toBeVisible();
  await expect(page.locator('img[src="/brand/kynetic-mark.svg"]').first()).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  expect(
    (await new AxeBuilder({ page }).exclude("nextjs-portal").analyze()).violations,
  ).toEqual([]);
  await page.screenshot({
    path: testInfo.outputPath("tenant-kynetic.png"),
    style: "nextjs-portal { display: none; }",
  });
});

test("a dev firm without mock branding uses Kien defaults", async ({ page }) => {
  await page.goto(`${serverOrigin("northwind.localhost")}/sign-in`);
  await expect(page.locator("html")).toHaveAttribute("data-firm-slug", "northwind");
  await expect(page.getByRole("heading", { name: "Sign in to Kien", exact: true })).toBeVisible();
  await expect(page.getByText("Kien", { exact: true }).first()).toBeVisible();
  await expect(page.locator('img[src="/brand/kien-mark.svg"]').first()).toBeVisible();
});

test("a production-style firm host resolves the same slug", async ({ page }) => {
  // Signed out, so the sign-in page (which carries the firm mark) is shown.
  await page.addInitScript(() => localStorage.setItem("ains-synthetic-signed-out", "true"));
  await page.goto(`${serverOrigin("kynetic.kiensolutions.com")}/sign-in`);
  await expect(page.locator("html")).toHaveAttribute("data-firm-slug", "kynetic");
  await expect(page.locator('img[src="/brand/kynetic-mark.svg"]').first()).toBeVisible();
});

test("apex, www, and a missing slug show the unknown firm page", async ({ page }, testInfo) => {
  await page.goto(`${serverOrigin("kiensolutions.com")}/`);
  await expectUnknownFirm(page, "apex");
  expect(
    (await new AxeBuilder({ page }).exclude("nextjs-portal").analyze()).violations,
  ).toEqual([]);
  await page.screenshot({
    path: testInfo.outputPath("unknown-firm.png"),
    style: "nextjs-portal { display: none; }",
  });

  await page.goto(`${serverOrigin("www.kiensolutions.com")}/auditor`);
  await expectUnknownFirm(page, "www");

  await page.goto(`${serverOrigin("www.localhost")}/`);
  await expectUnknownFirm(page, "www");

  await page.goto(`${serverOrigin("localhost")}/sign-in`);
  await expectUnknownFirm(page, "missing");

  await page.goto(`${serverOrigin("127.0.0.1")}/`);
  await expectUnknownFirm(page, "missing");
});
