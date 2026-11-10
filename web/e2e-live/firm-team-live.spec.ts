import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

test("team reads server state or shows unavailable, never inventing members", async ({ page }) => {
  await signIn(page);
  const response = page.waitForResponse((r) => r.url().endsWith("/auditor/firm/team"));
  await page.goto("/auditor/firm/team");
  const result = await response;
  await expect(page.getByTestId("mock-notice")).toHaveCount(0);
  if (result.status() === 404) {
    await expect(page.getByText("Not available yet", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Invite member" })).toBeDisabled();
    await page.getByRole("button", { name: "Try again" }).click();
    await expect(page.getByText("Not available yet", { exact: true })).toBeVisible();
  } else {
    expect(result.status()).toBe(200);
    const members = await result.json() as { name: string }[];
    await expect(page.getByRole("row")).toHaveCount(members.length + 1);
    for (const member of members) await expect(page.getByRole("cell").filter({ hasText: member.name }).first()).toBeVisible();
  }
});

test("client is redirected away from firm team settings", async ({ page }) => {
  await signIn(page, "client");
  await page.goto("/auditor/firm/team");
  await expect(page).toHaveURL(/localhost:3100\/$/);
  await expect(page.getByRole("heading", { name: "Team and roles" })).toHaveCount(0);
});
