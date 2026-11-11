import { expect, test, type Browser, type Page } from "@playwright/test";
import { AUDITOR_ORIGIN, callApi, portalOrigin, signInAt } from "./helpers";

/**
 * The Friday demo, one audit end to end on the REAL backend (scripts/e2e_backend.py), synthetic
 * data only. Steps run in order and share state; each later PR adds the next step.
 * Auditor works on http://kynetic.localhost:3100; the new client firm on http://<slug>.localhost:3100.
 */
test.describe.configure({ mode: "serial" });

const QUENTIN = "e2e-quentin@example.test";
const AUDITOR_PASSWORD = "synthetic-auditor-password";
const FIRM = "Synthetic Demo Securities";
const CLIENT_NAME = "Synthetic Demo Controller";
const CLIENT_EMAIL = "demo-controller@example.test";
const CLIENT_PASSWORD = "synthetic-demo-client-password";

const state: { slug: string; engagementId: string; firmId: string } = {
  slug: "",
  engagementId: "",
  firmId: "",
};

async function auditorPage(browser: Browser): Promise<Page> {
  const page = await (await browser.newContext()).newPage();
  await signInAt(page, AUDITOR_ORIGIN, QUENTIN, AUDITOR_PASSWORD, true, "/auditor");
  return page;
}

async function clientPage(browser: Browser): Promise<Page> {
  const page = await (await browser.newContext()).newPage();
  await signInAt(page, portalOrigin(state.slug), CLIENT_EMAIL, CLIENT_PASSWORD, false, "/");
  return page;
}

test("1. Quentin onboards a new client firm and the client accepts the invitation", async ({ browser }) => {
  const auditor = await auditorPage(browser);
  await auditor.goto(`${AUDITOR_ORIGIN}/auditor/workspaces/new`);
  await auditor.getByLabel("Firm name").fill(FIRM);
  await auditor.getByLabel("Review period start").fill("2025-01-01");
  await auditor.getByLabel("Review period end").fill("2025-12-31");
  await auditor.getByLabel("Target due date (optional)").fill("2026-12-15");
  await auditor.getByRole("button", { name: "Create workspace" }).click();
  await expect(auditor.getByText(`${FIRM} is ready`)).toBeVisible();
  await expect(auditor.getByText("all 34 canonical requests")).toBeVisible();
  state.slug = (await auditor.getByTestId("portal-slug").textContent())!.trim();
  expect(state.slug).toMatch(/^[a-z0-9-]+$/);

  // The new engagement is on the server, assigned to Quentin.
  const rows = (await callApi(auditor, AUDITOR_ORIGIN, "/auditor/engagements")).body as { id: string; firm: string; firmId?: string }[];
  const mine = rows.filter((row) => JSON.stringify(row).includes(FIRM));
  expect(mine).toHaveLength(1);
  state.engagementId = mine[0].id;

  // Invite the client contact; local preview mode returns the one-time link instead of email.
  await auditor.getByLabel("Client name").fill(CLIENT_NAME);
  await auditor.getByLabel("Client email").fill(CLIENT_EMAIL);
  await auditor.getByRole("button", { name: "Create invitation" }).click();
  const link = auditor.locator("a[href*=\"/accept-invitation?token=\"]").first();
  await expect(link).toBeVisible();
  const href = (await link.getAttribute("href"))!;
  expect(href).toContain("/accept-invitation?token=");

  // The client opens the link on their own firm portal, sets a password and lands in the portal.
  const client = await (await browser.newContext()).newPage();
  await client.goto(`${portalOrigin(state.slug)}${new URL(href, "http://x").pathname}${new URL(href, "http://x").search}`);
  await expect(client.getByText(FIRM).first()).toBeVisible();
  await client.getByLabel("Create password").fill(CLIENT_PASSWORD);
  await client.getByLabel("Confirm password").fill(CLIENT_PASSWORD);
  await client.getByRole("button", { name: "Set password and activate account" }).click();
  await expect(client).not.toHaveURL(/accept-invitation/);
  const current = await callApi(client, portalOrigin(state.slug), "/engagements/current");
  expect(current.status).toBe(200);
  expect((current.body as { id: string }).id).toBe(state.engagementId);

  // The same session cannot reach another firm's engagement.
  expect((await callApi(client, portalOrigin(state.slug), "/engagements/synthetic-other-engagement/progress")).status).toBe(404);
  // And Quentin's invitation list shows the invite as accepted.
  const invites = await callApi(auditor, AUDITOR_ORIGIN, `/auditor/engagements/${state.engagementId}/invitations`);
  expect(JSON.stringify(invites.body)).toContain("accepted");
});

// Later steps sign in again through these helpers.
void clientPage;
