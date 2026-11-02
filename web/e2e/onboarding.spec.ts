import { test, expect } from "./fixtures";
import AxeBuilder from "@axe-core/playwright";
for (const role of ["client", "auditor"]) {
  test(`${role} onboarding completes once and stays dismissed`, async ({
    page,
  }) => {
    await page.addInitScript((role) => {
      localStorage.setItem("ains-synthetic-role", role);
      localStorage.setItem("kien-synthetic-onboarding-enabled", "1");
    }, role);
    await page.goto(role === "auditor" ? "/auditor" : "/");
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    expect(
      (
        await new AxeBuilder({ page })
          .exclude("nextjs-portal")
          .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
          .analyze()
      ).violations,
    ).toEqual([]);
    await expect(
      dialog.getByRole("group", { name: "Step 1 of 3" }),
    ).toBeVisible();
    await dialog.getByRole("button", { name: "Next", exact: true }).click();
    await dialog.getByRole("button", { name: "Next", exact: true }).click();
    await dialog
      .getByRole("button", { name: "Get started", exact: true })
      .click();
    await expect(dialog).toBeHidden();
    await page.reload();
    await expect(dialog).toBeHidden();
    await page.setViewportSize({ width: 390, height: 844 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  });
  test(`${role} skip persists across reload`, async ({ page }) => {
    await page.addInitScript((role) => {
      localStorage.setItem("ains-synthetic-role", role);
      localStorage.setItem("kien-synthetic-onboarding-enabled", "1");
    }, role);
    await page.goto(role === "auditor" ? "/auditor" : "/");
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await dialog
      .getByRole("button", { name: "Skip tour", exact: true })
      .click();
    await expect(dialog).toBeHidden();
    await page.reload();
    await expect(dialog).toBeHidden();
  });
}

// Exercise the API path even in the synthetic build. State lives in the routed
// server fixture; a new browser context has no local onboarding storage.
for (const role of ["client", "auditor"] as const) {
  for (const dismissal of ["complete", "skip", "close", "escape"] as const) {
    test(`${role} server session persists ${dismissal} in a clean browser`, async ({
      browser,
    }) => {
      let state: "completed" | "skipped" | null = null;
      const methods: string[] = [];
      async function openBrowser() {
        const context = await browser.newContext();
        await context.addInitScript(() =>
          localStorage.setItem("ains-e2e-live-api", "1"),
        );
        await context.route("**/tenant/branding", (route) =>
          route.fulfill({
            json: {
              name: "Synthetic Onboarding Firm",
              logoUrl: null,
            },
          }),
        );
        await context.route("**/auth/session", (route) =>
          route.fulfill({
            json: {
              user: {
                id: `synthetic-${role}`,
                email: `${role}@example.invalid`,
                name: "Synthetic User",
                role,
                firm_id: "synthetic-firm",
                onboarding_state: state,
              },
            },
          }),
        );
        await context.route("**/auth/onboarding", async (route) => {
          methods.push(route.request().method());
          if (route.request().method() === "POST")
            state ??= route.request().postDataJSON().action;
          await route.fulfill({
            json: { state: state ?? "pending", flow: role },
          });
        });
        const page = await context.newPage();
        await page.goto(role === "auditor" ? "/auditor" : "/");
        await expect(page.locator("[data-page-header]").first()).toBeVisible();
        return { context, page };
      }
      const first = await openBrowser();
      const dialog = first.page.getByRole("dialog");
      await expect(dialog).toBeVisible();
      if (dismissal === "complete") {
        await dialog.getByRole("button", { name: "Next", exact: true }).click();
        await dialog.getByRole("button", { name: "Next", exact: true }).click();
        await dialog
          .getByRole("button", { name: "Get started", exact: true })
          .click();
      } else if (dismissal === "escape") {
        await first.page.keyboard.press("Escape");
      } else {
        await dialog
          .getByRole("button", {
            name: dismissal === "skip" ? "Skip tour" : "Close",
            exact: true,
          })
          .click();
      }
      await expect(dialog).toBeHidden();
      expect(state).toBe(dismissal === "complete" ? "completed" : "skipped");
      await first.page.reload();
      await expect(
        first.page.locator("[data-page-header]").first(),
      ).toBeVisible();
      await expect(dialog).toBeHidden();
      await first.context.close();
      const fresh = await openBrowser();
      await expect(fresh.page.getByRole("dialog")).toBeHidden();
      expect(methods).toEqual(["POST"]); // Session alone gates the UI; no GET needed.
      await fresh.context.close();
    });
  }

  test(`${role} failed dismissal stays open and retries the server save`, async ({
    page,
  }) => {
    await page.addInitScript(() =>
      localStorage.setItem("ains-e2e-live-api", "1"),
    );
    await page.route("**/tenant/branding", (route) =>
      route.fulfill({ json: { name: "Synthetic Firm", logoUrl: null } }),
    );
    await page.route("**/auth/session", (route) =>
      route.fulfill({
        json: {
          user: {
            id: `synthetic-${role}`,
            email: `${role}@example.invalid`,
            name: "Synthetic User",
            role,
            firm_id: "synthetic-firm",
            onboarding_state: null,
          },
        },
      }),
    );
    let attempts = 0;
    await page.route("**/auth/onboarding", (route) => {
      expect(route.request().method()).toBe("POST");
      attempts += 1;
      return attempts === 1
        ? route.fulfill({
            status: 503,
            json: { detail: "Could not save your preference. Please retry." },
          })
        : route.fulfill({ json: { state: "skipped", flow: role } });
    });
    await page.goto(role === "auditor" ? "/auditor" : "/");
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await dialog.getByRole("button", { name: "Close", exact: true }).click();
    await expect(dialog.getByRole("alert")).toContainText("Please retry");
    await expect(dialog).toBeVisible();
    await dialog
      .getByRole("button", { name: "Skip tour", exact: true })
      .click();
    await expect(dialog).toBeHidden();
    expect(attempts).toBe(2);
  });
}
