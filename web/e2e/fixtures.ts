import { test as base } from "@playwright/test";

export { expect, type Page } from "@playwright/test";

// Most existing journeys start in the client portal. Set the role explicitly:
// demo hosts now default to auditor. Preserve role changes across reloads.
// Seeded dates (deadlines, due tasks, activity) are hardcoded, so fix the browser clock to the
// day they were authored for. Otherwise lists like "Upcoming deadlines" change as time passes.
const FIXED_NOW = new Date("2026-11-02T12:00:00");

export const test = base.extend({
  page: async ({ page }, run) => {
    await page.clock.setFixedTime(FIXED_NOW);
    await page.addInitScript(() => {
      if (!localStorage.getItem("ains-synthetic-role")) {
        localStorage.setItem("ains-synthetic-role", "client");
      }
    });
    await run(page);
  },
});
