import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("auditor creates a workspace and manages a single-use synthetic client invitation", async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => localStorage.setItem("ains-synthetic-role", "auditor"));
  await page.goto("/auditor");

  await page.goto("/auditor/settings");
  await page.getByRole("button", { name: /Kien Operations/ }).click();
  await page.getByLabel("Current authenticator code").fill("123456");
  await page.getByRole("button", { name: "Replace recovery codes" }).click();
  await expect(page.getByText("Previous unused codes are revoked.")).toBeVisible();
  await page.getByRole("link", { name: "Add client workspace" }).click();
  await expect(page.getByRole("heading", { name: "Add client workspace" })).toBeVisible();
  await page.getByLabel("Firm name").fill("Synthetic Gamma Securities");
  await page.getByLabel("Review period start").fill("2026-01-01");
  await page.getByLabel("Review period end").fill("2026-12-31");
  await page.getByLabel("Target due date (optional)").fill("2027-02-15");
  await page.getByRole("button", { name: "Create workspace" }).click();

  await expect(page.getByRole("heading", { name: "Synthetic Gamma Securities is ready" })).toBeVisible();
  await expect(page.getByText("No client login exists yet.")).toBeVisible();
  await page.getByLabel("Client name").fill("Synthetic Gamma Client");
  await page.getByLabel("Client email").fill("gamma-client@example.test");
  await page.getByRole("button", { name: "Create invitation" }).click();

  const email = page.getByRole("article", { name: "Invitation email preview" });
  await expect(email.getByText("You're invited to Kien", { exact: true })).toBeVisible();
  await expect(email.getByText("Kien by Kien Solutions", { exact: true })).toBeVisible();
  await expect(email.getByRole("link", { name: "kiensolutions.com" })).toHaveAttribute(
    "href",
    "https://kiensolutions.com",
  );
  await expect(email.getByText("gamma-client@example.test")).toBeVisible();
  const preview = email.getByRole("link", { name: "Open invitation preview" });
  await expect(preview).toBeVisible();
  const firstHref = await preview.getAttribute("href");
  await page.getByRole("button", { name: "Revoke invitation" }).click();
  await expect(page.getByText("revoked", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Resend invitation" }).click();
  await expect(page.getByText("pending", { exact: true })).toBeVisible();
  const reissuedHref = await preview.getAttribute("href");
  expect(reissuedHref).not.toBe(firstHref);

  await page.goto(reissuedHref!);
  await expect(page.getByRole("heading", { name: "Accept client invitation" })).toBeVisible();
  await expect(page.getByText("Synthetic demo only.")).toBeVisible();
  expect(
    (
      await new AxeBuilder({ page })
        .exclude("nextjs-portal")
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page.getByLabel("Create password").fill("synthetic-password-123");
  await page.getByLabel("Confirm password").fill("synthetic-password-123");
  await page.getByRole("button", { name: "Set password and activate account" }).click();
  await expect(page.getByRole("heading", { name: "Example Securities LLC" })).toBeVisible();
});
