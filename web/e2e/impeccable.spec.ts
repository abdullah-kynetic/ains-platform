import { expect, test } from "@playwright/test";

for (const role of ["client", "auditor"] as const) {
  test(`${role} long firm heading remains readable at narrow and zoom-sized widths`, async ({ page }) => {
    await page.addInitScript((role) => localStorage.setItem("ains-synthetic-role", role), role);
    for (const width of [1440, 768, 390]) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(role === "auditor" ? "/auditor" : "/");
      const title = page.locator("[data-page-header] h1");
      await expect(title).toBeVisible();
      // Stress the existing variable-content role without persisting a firm edit.
      await title.evaluate((element) => {
        element.textContent = `SyntheticFirm${"LongIdentifier".repeat(35)}`;
      });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      expect(await title.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
    }
  });
}

test("sidebar retains the first touch pointer and recovers after blur", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  const handle = page.getByRole("separator", { name: "Resize sidebar" });
  const sidebar = page.locator(".desktop-sidebar");
  await expect(handle).toHaveAttribute("aria-valuenow", "256");
  const box = await handle.boundingBox();
  if (!box) throw new Error("Sidebar handle is missing");
  const x = box.x + box.width / 2;
  const y = box.y + 100;
  const cdp = await page.context().newCDPSession(page);
  const first = (offset: number) => ({ x: x + offset, y, id: 1 });
  const second = { x: x + 32, y: y + 60, id: 2 };
  await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [first(0)] });
  await cdp.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [first(32)] });
  await expect(handle).toHaveAttribute("aria-valuenow", "288");
  await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [first(32), second] });
  await cdp.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [first(48), second] });
  await expect(handle).toHaveAttribute("aria-valuenow", "304");
  // A cancellation for a different pointer must not cancel the owning drag.
  await handle.dispatchEvent("pointercancel", { pointerId: 999, pointerType: "touch" });
  await expect(sidebar).toHaveAttribute("data-dragging", "true");
  await page.evaluate(() => window.dispatchEvent(new Event("blur")));
  await expect(sidebar).toHaveAttribute("data-dragging", "false");
  await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
  const next = await handle.boundingBox();
  if (!next) throw new Error("Sidebar handle is missing after blur");
  await page.mouse.move(next.x + next.width / 2, y);
  await page.mouse.down();
  await page.mouse.move(next.x + next.width / 2 + 16, y);
  await page.mouse.up();
  await expect(handle).toHaveAttribute("aria-valuenow", "320");
});

test("long report prose remains readable in the phone print view", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("ains-synthetic-role", "auditor"));
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/auditor/reports");
  await page.getByRole("button", { name: "Draft report", exact: true }).first().click();
  const text = `SyntheticReference${"LongUnbrokenIdentifier".repeat(40)}`;
  await page.getByRole("textbox", { name: "Scope", exact: true }).fill(text);
  await page.getByRole("button", { name: "Save draft", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "Draft saved." })).toBeVisible();
  await page.getByRole("link", { name: "Print view", exact: true }).click();
  const prose = page.locator(".report-rich").filter({ hasText: text }).first();
  await expect(prose).toContainText(text);
  expect(await prose.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
