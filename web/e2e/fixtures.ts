import { test as base } from "@playwright/test";

export { expect, type Page } from "@playwright/test";

// Most existing journeys start in the client portal. Set the role explicitly:
// demo hosts now default to auditor. Preserve role changes across reloads.
export const test = base.extend({
  page: async ({ page }, run) => {
    await page.addInitScript(() => {
      if (!localStorage.getItem("ains-synthetic-role")) {
        localStorage.setItem("ains-synthetic-role", "client");
      }
    });
    await run(page);
  },
});
