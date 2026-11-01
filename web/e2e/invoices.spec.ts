import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

async function auditor(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.evaluate(() =>
    localStorage.setItem("ains-synthetic-role", "auditor"),
  );
  await page.goto("/auditor/invoices");
}

test("auditor creates, edits, sends and pays an invoice with persistent payment history", async ({
  page,
}) => {
  await auditor(page);
  await expect(
    page.getByRole("link", { name: "Invoices", exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Create invoice" }).click();
  await page
    .getByLabel("Description 1", { exact: true })
    .fill("Synthetic independent review");
  await page.getByLabel("Quantity 1", { exact: true }).fill("1.25");
  await page.getByLabel("Rate 1 (USD)", { exact: true }).fill("10.02");
  await page.getByRole("button", { name: "Add line" }).click();
  await page
    .getByLabel("Description 2", { exact: true })
    .fill("Synthetic preparation");
  await page.getByLabel("Rate 2 (USD)", { exact: true }).fill("5.00");
  await expect(page.getByLabel("Invoice total")).toHaveText("$17.53");
  await page.getByRole("button", { name: "Save draft" }).click();
  await expect(
    page.getByRole("heading", { name: "INV-0005", exact: true, level: 1 }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Edit draft" }).click();
  await page.getByLabel("Invoice notes").fill("Synthetic payment reference");
  await page.getByRole("button", { name: "Save draft" }).click();
  await expect(page.getByText("Synthetic payment reference")).toBeVisible();
  await page.getByRole("button", { name: "Mark sent" }).click();
  await page.getByRole("button", { name: "Mark paid" }).click();
  const dialog = page.getByRole("dialog", { name: "Record payment" });
  await expect(dialog).toBeVisible();
  await dialog.getByLabel("Amount received (USD)").fill("5.00");
  await dialog.getByRole("button", { name: "Record payment" }).click();
  await expect(dialog).not.toBeVisible();
  await page.getByRole("button", { name: "Mark paid" }).click();
  await expect(dialog.getByLabel("Amount received (USD)")).toHaveValue("12.53");
  await dialog.getByRole("button", { name: "Record payment" }).click();
  await expect(page.getByRole("button", { name: "Mark paid" })).toHaveCount(0);
  await page.reload();
  await expect(page.getByText("paid", { exact: true }).first()).toBeVisible();
  await expect(page.getByText(/payment · \$5.00/i)).toBeVisible();
  await expect(page.getByText(/payment · \$12.53/i)).toBeVisible();
  await page.emulateMedia({ media: "print" });
  await expect(page.locator(".invoice-print")).toBeVisible();
  await expect(page.locator(".invoice-controls").first()).not.toBeVisible();
});

test("invoice filters, void confirmation, mobile and accessible form", async ({
  page,
}) => {
  await auditor(page);
  await page.getByLabel("Status", { exact: true }).selectOption("overdue");
  await expect(
    page
      .getByRole("list", { name: "Invoices", exact: true })
      .getByRole("listitem"),
  ).toHaveCount(1);
  await page.getByRole("link", { name: /INV-0003/ }).click();
  await page.getByRole("button", { name: "Void invoice" }).click();
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await page.getByRole("button", { name: "Void invoice" }).click();
  await page.getByRole("button", { name: "Confirm void" }).click();
  await expect(page.getByText("Void", { exact: true }).first()).toBeVisible();
  await page.goto("/auditor/invoices/new");
  await expect(page.getByLabel("Description 1", { exact: true })).toBeVisible();
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await expect(page.getByRole("button", { name: "Save draft" })).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.goto("/auditor/invoices");
  await expect(
    page.getByRole("heading", { name: "Invoices", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("client has no invoice navigation and cannot open any invoice URL", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("link", { name: "Invoices", exact: true }),
  ).toHaveCount(0);
  for (const path of [
    "/auditor/invoices",
    "/auditor/invoices/new",
    "/auditor/invoices/invoice-synthetic-1",
    "/auditor/invoices/invoice-synthetic-1/edit",
  ]) {
    await page.goto(path);
    await expect(page).toHaveURL(/\/$/);
    await expect(
      page.getByRole("link", { name: "Invoices", exact: true }),
    ).toHaveCount(0);
    await expect(page.getByRole("heading", { name: /^INV-/ })).toHaveCount(0);
  }
});
