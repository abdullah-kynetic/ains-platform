import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

test("rubric and templates read server state or show unavailable", async ({ page }) => {
  await signIn(page);
  for (const [tab, route] of [["rubric", "/auditor/firm/rubric"], ["templates", "/auditor/firm/request-templates"]]) {
    const response = page.waitForResponse((r) => r.url().endsWith(route));
    await page.goto(`/auditor/firm/${tab}`);
    const result = await response;
    if (result.status() === 404) {
      await expect(page.getByText("Not available yet", { exact: true })).toBeVisible();
      await expect(page.getByPlaceholder("Pass criteria (set by the partner)")).toHaveCount(0);
      if (tab === "templates") await expect(page.getByRole("button", { name: "New template" })).toBeDisabled();
    } else {
      expect(result.status()).toBe(200);
      const rows = await result.json() as { requestId?: string; name?: string }[];
      for (const row of rows) await expect(page.getByText(row.requestId ?? row.name ?? "", { exact: true }).first()).toBeVisible();
    }
    await expect(page.getByTestId("mock-notice")).toHaveCount(0);
  }
});

test("client cannot open auditor rubric or templates", async ({ page }) => {
  await signIn(page, "client");
  for (const tab of ["rubric", "templates"]) {
    await page.goto(`/auditor/firm/${tab}`);
    await expect(page).toHaveURL(/localhost:3100\/$/);
  }
});
