import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const landingURL = "http://127.0.0.1:3110";

async function openLanding(page: import("@playwright/test").Page) {
  await page.goto(landingURL);
  await page.evaluate(() => document.fonts.ready);
}

test("public landing page states the service and the contact email", async ({
  page,
}) => {
  await openLanding(page);
  await expect(page).toHaveTitle(/Kien/);
  await expect(
    page.getByRole("heading", { level: 1, name: "AI-assisted AML independent testing for broker-dealers." }),
  ).toBeVisible();
  await expect(page.getByText("Kien by Kien Solutions").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "How it works" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Benefits" })).toBeVisible();

  const mail = page.locator('a[href="mailto:abdullah@kiensolutions.com"]');
  await expect(mail).toHaveCount(3);
  await expect(mail.first()).toBeVisible();

  const body = await page.locator("body").innerText();
  expect(body).not.toMatch(/\d+%/);
  expect(body).not.toMatch(/\$\d/);
  await expect(
    page.getByRole("heading", { name: /testimonial|trusted by|our clients/i }),
  ).toHaveCount(0);

  for (const scheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme: scheme });
    await openLanding(page);
    const background = await page.evaluate(
      () => getComputedStyle(document.body).backgroundColor,
    );
    expect(background).toBe(scheme === "dark" ? "rgb(51, 64, 92)" : "rgb(246, 242, 233)");
    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(result.violations, `${scheme}: ${JSON.stringify(result.violations)}`).toEqual([]);
  }
});

test("landing page keeps the contact link on a phone width", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openLanding(page);
  const overflows = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
  );
  expect(overflows).toBe(false);
  await expect(
    page.getByRole("link", { name: "abdullah@kiensolutions.com" }).first(),
  ).toBeVisible();
  await page.getByRole("link", { name: "How it works" }).click();
  await expect(page.getByRole("heading", { name: "How it works" })).toBeInViewport();
});
