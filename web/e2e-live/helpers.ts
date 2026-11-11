import { expect, type Page } from "@playwright/test";

export const API = "http://kynetic.localhost:8000";
export const OTHER_ENGAGEMENT = "synthetic-other-engagement";

export async function signIn(page: Page, role: "auditor" | "client" = "auditor") {
  await page.goto(`/sign-in?next=${encodeURIComponent(role === "auditor" ? "/auditor" : "/")}`);
  await page.getByLabel("Email", { exact: true }).fill(`e2e-${role}@example.test`);
  await page.getByLabel("Password", { exact: true }).fill(`synthetic-${role}-password`);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).not.toHaveURL(/sign-in/);
  const skip = page.getByRole("button", { name: "Skip tour" });
  if (await skip.isVisible()) await skip.click();
}

export async function backend(page: Page, path: string, method = "GET", data?: unknown) {
  return page.evaluate(async ({ url, method, data }) => {
    const response = await fetch(url, { method, credentials: "include",
      ...(data === undefined ? {} : { headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) }),
    });
    return { status: response.status, body: await response.json() };
  }, { url: `${API}${path}`, method, data });
}

export async function ownEngagement(page: Page): Promise<string> {
  const response = await backend(page, "/auditor/engagements");
  expect(response.status).toBe(200);
  const rows = response.body as { id: string }[];
  expect(rows).toHaveLength(1);
  return rows[0].id;
}

/** Auditor host for the demo journey (the web app needs a known firm host locally). */
export const AUDITOR_ORIGIN = "http://kynetic.localhost:3100";
export const portalOrigin = (slug: string) => `http://${slug}.localhost:3100`;
export const apiFor = (origin: string) => origin.replace(":3100", ":8000");

/** Sign in on a given origin. The throwaway backend has no email key, so sign-in is email + password only. Synthetic test-only credentials. */
export async function signInAt(page: Page, origin: string, email: string, password: string, _legacyMfaFlag: boolean, next = "/") {
  await page.goto(`${origin}/sign-in?next=${encodeURIComponent(next)}`);
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).not.toHaveURL(/sign-in/);
  const skip = page.getByRole("button", { name: "Skip tour" });
  if (await skip.isVisible().catch(() => false)) await skip.click();
}

/** Call the API from inside the page, so the page's own session cookie is used. */
export async function callApi(page: Page, origin: string, path: string, method = "GET", data?: unknown) {
  return page.evaluate(async ({ url, method, data }) => {
    const response = await fetch(url, { method, credentials: "include",
      ...(data === undefined ? {} : { headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) }),
    });
    const text = await response.text();
    let body: unknown = null;
    try { body = JSON.parse(text); } catch { body = text; }
    return { status: response.status, body };
  }, { url: `${apiFor(origin)}${path}`, method, data });
}
