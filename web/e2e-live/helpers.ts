import { execFileSync } from "node:child_process";
import { expect, type Page } from "@playwright/test";

export const API = "http://kynetic.localhost:8000";
export const OTHER_ENGAGEMENT = "synthetic-other-engagement";

export async function signIn(page: Page, role: "auditor" | "client" = "auditor") {
  await page.goto(`/sign-in?next=${encodeURIComponent(role === "auditor" ? "/auditor" : "/")}`);
  await page.getByLabel("Email", { exact: true }).fill(`e2e-${role}@example.test`);
  await page.getByLabel("Password", { exact: true }).fill(`synthetic-${role}-password`);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  if (role === "auditor") {
    const code = execFileSync("../.venv/bin/python", ["-c",
      'import runpy,pyotp; f=runpy.run_path("../scripts/e2e_backend.py"); print(pyotp.TOTP(f["MFA_SECRET"]).now())',
    ], { encoding: "utf8" }).trim();
    await page.getByLabel("Authenticator or recovery code").fill(code);
    await page.getByRole("button", { name: "Verify", exact: true }).click();
  }
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
