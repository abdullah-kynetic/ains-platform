import { expect, test } from "@playwright/test";
import { API, signIn } from "./helpers";

test("branding contract has no local-storage fallback or pretend logo upload", async ({ page }) => {
  await signIn(page);
  const response = page.waitForResponse((r) => r.request().method() === "GET" && r.url().startsWith(API) && r.url().endsWith("/auditor/firm/branding"));
  await page.goto("/auditor/firm/branding");
  const result = await response;
  if (result.status() === 404) {
    await expect(page.getByText("Not available yet", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Upload logo" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Save branding" })).toHaveCount(0);
  } else {
    expect(result.status()).toBe(200);
    const branding = await result.json() as { name: string };
    await expect(page.getByLabel("Firm name", {exact: true})).toHaveValue(branding.name);
  }
  expect(await page.evaluate(() => localStorage.getItem("kien-mock-brand-v1"))).toBeNull();
});

test("client cannot open auditor branding settings", async ({ page }) => {
  await signIn(page, "client");
  await page.goto("/auditor/firm/branding");
  await expect(page).toHaveURL(/localhost:3100\/$/);
  await expect(page.getByRole("heading", { name: "Branding", exact: true })).toHaveCount(0);
});
