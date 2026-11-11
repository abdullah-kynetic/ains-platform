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

test("2. Quentin sends the numbered checklist; the client sees it was sent", async ({ browser }) => {
  const client = await clientPage(browser);
  await client.goto(`${portalOrigin(state.slug)}/`);
  await expect(client.getByTestId("checklist-status")).toContainText("has not sent the checklist yet");

  const auditor = await auditorPage(browser);
  await auditor.goto(`${AUDITOR_ORIGIN}/auditor/engagements/${state.engagementId}`);
  const card = auditor.getByTestId("client-checklist-card");
  await expect(card.getByTestId("workflow-stage")).toHaveText("Checklist not sent");
  await card.getByRole("button", { name: "Send checklist to client" }).click();
  await expect(card.getByTestId("workflow-stage")).toHaveText("Checklist sent");
  // Recorded once on the server: a second send is refused.
  expect((await callApi(auditor, AUDITOR_ORIGIN, `/auditor/engagements/${state.engagementId}/checklist/send`, "POST")).status).toBe(409);
  // Firm isolation: Quentin cannot send another firm's checklist; the client cannot send at all.
  expect((await callApi(auditor, AUDITOR_ORIGIN, "/auditor/engagements/synthetic-other-engagement/checklist/send", "POST")).status).toBe(404);
  expect((await callApi(client, portalOrigin(state.slug), `/auditor/engagements/${state.engagementId}/checklist/send`, "POST")).status).toBe(403);

  await client.goto(`${portalOrigin(state.slug)}/checklist`);
  await expect(client.getByTestId("checklist-status")).toContainText("Your auditor sent the checklist");
  const progress = await callApi(client, portalOrigin(state.slug), `/engagements/${state.engagementId}/progress`);
  expect((progress.body as { stage: string; items: unknown[] }).stage).toBe("checklist_sent");
  expect((progress.body as { items: unknown[] }).items).toHaveLength(34);
});

test("3. The client asks for N/A with reasons; Quentin approves one and rejects one", async ({ browser }) => {
  const client = await clientPage(browser);
  const portal = portalOrigin(state.slug);
  await client.goto(`${portal}/checklist`);
  for (const [request, reason] of [
    ["AML-BD-020", "The firm does not open accounts for foreign financial institutions."],
    ["AML-BD-021", "The firm has no private banking accounts."],
  ]) {
    const row = client.getByTestId(`request-${request}`);
    await row.getByRole("button", { name: `Does not apply: ${request}` }).click();
    await row.getByLabel(`Why does ${request} not apply to your firm?`).fill(reason);
    await row.getByRole("button", { name: "Send to auditor" }).click();
    await expect(row).toContainText("Waiting for your auditor");
  }
  // Clients can no longer declare N/A directly.
  const progress = (await callApi(client, portal, `/engagements/${state.engagementId}/progress`)).body as { items: { id: string; requestId: string }[] };
  const itemId = (rid: string) => progress.items.find((i) => i.requestId === rid)!.id;
  expect((await callApi(client, portal, `/engagements/${state.engagementId}/items/${itemId("AML-BD-022")}/na`, "POST", { not_applicable: true })).status).toBe(409);
  // The questionnaire can no longer mark N/A either, and its old review route is gone.
  const questionnaire = await callApi(client, portal, `/engagements/${state.engagementId}/questionnaire`);
  const question = (questionnaire.body as { questions: { itemId: string }[] }).questions[0];
  if (question) {
    expect((await callApi(client, portal, `/engagements/${state.engagementId}/questionnaire/answers`, "POST", { answers: [{ itemId: question.itemId, applies: false }] })).status).toBe(422);
    expect([404, 405]).toContain((await callApi(client, portal, `/engagements/${state.engagementId}/questionnaire/items/${question.itemId}/na-review`, "POST", { decision: "approve" })).status);
  }
  // A client cannot decide its own request.
  expect((await callApi(client, portal, `/auditor/engagements/${state.engagementId}/items/${itemId("AML-BD-020")}/na-request/decision`, "POST", { decision: "accept" })).status).toBe(403);

  const auditor = await auditorPage(browser);
  await auditor.goto(`${AUDITOR_ORIGIN}/auditor/engagements/${state.engagementId}/client-checklist`);
  await auditor.getByTestId("na-request-AML-BD-020").getByRole("button", { name: "Approve N/A" }).click();
  await expect(auditor.getByTestId("na-request-AML-BD-020")).toHaveCount(0);
  const reject = auditor.getByTestId("na-request-AML-BD-021");
  await reject.getByLabel("Note to the client (required to reject)").fill("Please confirm in writing; the questionnaire says private banking exists.");
  await reject.getByRole("button", { name: "Reject" }).click();
  await expect(auditor.getByTestId("na-request-AML-BD-021")).toHaveCount(0);
  await expect(auditor.getByTestId("client-item-AML-BD-020")).toContainText("Does not apply");
  await expect(auditor.getByTestId("client-item-AML-BD-021")).toContainText("N/A rejected");
  // Quentin cannot decide on another firm's items.
  expect((await callApi(auditor, AUDITOR_ORIGIN, `/auditor/engagements/synthetic-other-engagement/items/${itemId("AML-BD-021")}/na-request/decision`, "POST", { decision: "accept" })).status).toBe(404);

  await client.reload();
  await expect(client.getByTestId("section-na")).toContainText("AML-BD-020");
  await expect(client.getByTestId("request-AML-BD-021")).toContainText("Your auditor needs this request: Please confirm in writing");
});

const pdf = (name: string) => ({ name, mimeType: "application/pdf", buffer: Buffer.from(`%PDF-1.4\n% Synthetic demo document: ${name}\n%%EOF\n`) });

test("4. The client uploads numbered documents, maps them to requests and submits; Quentin accepts", async ({ browser }) => {
  const client = await clientPage(browser);
  const portal = portalOrigin(state.slug);
  await client.goto(`${portal}/upload`);
  await client.locator("input[type=file]").setInputFiles([
    pdf("synthetic-aml-policy.pdf"),
    pdf("synthetic-cip-procedures.pdf"),
    pdf("synthetic-training-log.pdf"),
  ]);
  await client.getByLabel("I have checked the files for this engagement.").check();
  await client.getByRole("button", { name: "Confirm and upload" }).click();
  for (const n of ["1.1", "1.2", "1.3"]) await expect(client.getByText(`Received as document ${n}`)).toBeVisible();

  await client.goto(`${portal}/checklist`);
  for (const [request, doc] of [["AML-BD-001", "1.1"], ["AML-BD-001", "1.2"], ["AML-BD-002", "1.2"], ["AML-BD-003", "1.3"]]) {
    const row = client.getByTestId(`request-${request}`);
    const select = row.getByLabel(`Map a document to ${request}`);
    const value = await select.locator("option", { hasText: `${doc} ·` }).getAttribute("value");
    await select.selectOption(value!);
    await row.getByRole("button", { name: "Map", exact: true }).click();
    await expect(row.getByLabel(`Documents for ${request}`)).toContainText(doc);
  }
  // Unmapping works and is reversible.
  const first = client.getByTestId("request-AML-BD-001");
  await first.getByRole("button", { name: "Unlink 1.2 from AML-BD-001" }).click();
  await expect(first.getByLabel("Documents for AML-BD-001")).not.toContainText("1.2");
  await first.getByRole("button", { name: "Submit AML-BD-001 to auditor" }).click();
  await expect(first).toContainText("With auditor");
  await client.getByRole("button", { name: "Submit all ready requests" }).click();
  await expect(client.getByRole("status").filter({ hasText: "with your auditor." })).toContainText("3 requests with your auditor");
  await expect(client.getByTestId("request-AML-BD-003")).toContainText("With auditor");

  // Isolation: the client cannot upload to, or link into, another firm's engagement.
  const docs = (await callApi(client, portal, "/engagements/current")).body as { unassignedDocuments: { id: string; number: string }[] };
  expect(docs.unassignedDocuments.map((d) => d.number).sort()).toEqual(["1.1", "1.2", "1.3"]);
  expect((await callApi(client, portal, `/engagements/synthetic-other-engagement/items/x/documents/${docs.unassignedDocuments[0].id}/link`, "POST")).status).toBe(404);

  const auditor = await auditorPage(browser);
  await auditor.goto(`${AUDITOR_ORIGIN}/auditor/engagements/${state.engagementId}/client-checklist`);
  const row = auditor.getByTestId("client-item-AML-BD-001");
  await expect(row).toContainText("1.1");
  await row.getByRole("button", { name: "Accept AML-BD-001 for testing" }).click();
  await expect(row).toContainText("Accepted for testing");
  await expect(auditor.getByTestId("client-item-AML-BD-002")).toContainText("With auditor");
  expect((await callApi(auditor, AUDITOR_ORIGIN, "/auditor/engagements/synthetic-other-engagement/items/x/accept", "POST")).status).toBe(404);
});

test("5. Quentin flags a document; the client replies in Messages; Quentin resolves", async ({ browser }) => {
  const auditor = await auditorPage(browser);
  await auditor.goto(`${AUDITOR_ORIGIN}/auditor/engagements/${state.engagementId}/client-checklist`);
  const row = auditor.getByTestId("client-item-AML-BD-002");
  await row.getByRole("button", { name: "Flag AML-BD-002" }).click();
  await auditor.getByLabel("Problem type").selectOption("outdated");
  await auditor.getByLabel("Which document").selectOption({ label: "1.2 · synthetic-cip-procedures.pdf" });
  await auditor.getByLabel(/Note to the client/).fill("This policy is dated 2023. Please send the 2025 version.");
  await auditor.getByRole("button", { name: "Send to client" }).click();
  await expect(row).toContainText("Needs information");
  await expect(auditor.getByTestId("issue-threads")).toContainText("This policy is dated 2023");

  const client = await clientPage(browser);
  const portal = portalOrigin(state.slug);
  await client.goto(`${portal}/messages`);
  const thread = client.locator("[data-testid^=issue-]").first();
  await expect(thread).toContainText("This policy is dated 2023");
  await thread.getByLabel("Reply").fill("Uploading the 2025 version now.");
  await thread.getByRole("button", { name: "Send reply" }).click();
  await expect(thread).toContainText("Uploading the 2025 version now.");
  // Clients never see findings or auditor-only fields.
  await expect(client.getByText(/finding/i)).toHaveCount(0);

  await auditor.reload();
  const t = auditor.getByTestId("issue-threads").locator("[data-testid^=issue-]").first();
  await expect(t).toContainText("Uploading the 2025 version now.");
  await t.getByRole("button", { name: "Mark resolved" }).click();
  await expect(t).toContainText("Resolved");
  await expect(auditor.getByTestId("client-item-AML-BD-002")).toContainText("With auditor");

  // Isolation: threads of this firm are invisible and unwritable from another engagement id.
  expect((await callApi(auditor, AUDITOR_ORIGIN, "/auditor/engagements/synthetic-other-engagement/issues")).status).toBe(404);
  expect((await callApi(client, portal, "/engagements/synthetic-other-engagement/issues")).status).toBe(404);
});

test("5b. Quentin records a finding and asks for a management response; the client answers without ever seeing the finding", async ({ browser }) => {
  test.setTimeout(120_000);
  const auditor = await auditorPage(browser);
  const audit = `/auditor/engagements/${state.engagementId}`;
  await auditor.goto(`${AUDITOR_ORIGIN}${audit}/findings`);
  await auditor.getByRole("button", { name: "New finding" }).first().click();
  await auditor.getByLabel("Title", { exact: true }).fill("Synthetic training log is incomplete");
  await auditor.getByLabel("Rule cited").fill("FINRA Rule 3310(e)");
  await auditor.getByLabel("Condition").fill("SECRETFINDINGCONDITION: two staff have no training record.");
  await auditor.getByLabel("Cause").fill("SECRETFINDINGCAUSE");
  await auditor.getByLabel("Effect").fill("SECRETFINDINGEFFECT");
  await auditor.getByLabel("Recommendation").fill("SECRETFINDINGRECOMMENDATION");
  await auditor.getByRole("button", { name: "Add citation" }).click();
  await auditor.getByLabel("Citation 1 document").selectOption({ index: 1 });
  await auditor.getByLabel("Citation 1 page").fill("2");
  await auditor.getByRole("button", { name: "Save draft" }).click();
  await auditor.getByRole("button", { name: "Approve", exact: true }).click();
  await auditor.getByRole("button", { name: "Request response" }).click();
  await auditor.getByLabel("Title for the client").fill("Training records for two staff");
  await auditor.getByLabel("Request", { exact: true }).fill("Please confirm when training records for two staff will be completed.");
  await auditor.getByRole("button", { name: "Release to client" }).click();
  await expect(auditor.getByText("Requested from the client; awaiting their response.")).toBeVisible();

  // The client sees only the request the auditor wrote, never the finding.
  const client = await clientPage(browser);
  const portal = portalOrigin(state.slug);
  await client.goto(`${portal}/responses`);
  await expect(client.getByRole("heading", { name: "Training records for two staff" })).toBeVisible();
  await expect(client.getByText("Please confirm when training records")).toBeVisible();
  const page = await client.locator("body").innerText();
  expect(page).not.toMatch(/SECRETFINDING|Synthetic training log is incomplete|Rule 3310\(e\)/);
  await client.getByLabel("Your response").fill("Training will be completed by 15 January.");
  await client.getByRole("button", { name: "Submit response" }).click();
  await expect(client.getByText("Response sent")).toBeVisible();

  // Quentin sees the response on the finding and closes it.
  await auditor.goto(`${AUDITOR_ORIGIN}${audit}/findings`);
  await expect(auditor.getByText("Training will be completed by 15 January.")).toBeVisible();
  await auditor.getByRole("button", { name: "Close finding" }).click();
  await expect(auditor.getByText("Closed", { exact: true }).first()).toBeVisible();
});

test("6. Quentin concludes, a second reviewer approves, Quentin signs; the client confirms; an invoice is issued", async ({ browser }) => {
  test.setTimeout(180_000);
  const REVIEWER = "e2e-reviewer@example.test";
  const auditor = await auditorPage(browser);
  const audit = `/auditor/engagements/${state.engagementId}`;

  // Conclusions: the first five through the screen, the rest through the same route the screen calls.
  await auditor.goto(`${AUDITOR_ORIGIN}${audit}/checklist`);
  for (const n of ["001", "002", "003", "004", "005"]) {
    const select = auditor.getByLabel(new RegExp(`Conclusion for AML-BD-${n} `));
    await select.selectOption("pass");
    await expect(select).toHaveValue("pass");
  }
  const tests = (await callApi(auditor, AUDITOR_ORIGIN, `${audit}/checklist-tests`)).body as { requestId: string; conclusion: string | null }[];
  expect(tests).toHaveLength(34);
  const open = tests.filter((x) => x.conclusion === null);
  for (let i = 0; i < open.length; i += 6) {
    const results = await Promise.all(open.slice(i, i + 6).map((t) => callApi(auditor, AUDITOR_ORIGIN, `${audit}/checklist-tests/${t.requestId}`, "PATCH", { conclusion: "pass" })));
    for (const r of results) expect(r.status).toBe(200);
  }

  // Independence is declared on its screen.
  await auditor.goto(`${AUDITOR_ORIGIN}${audit}/independence`);
  await expect(auditor.getByLabel("No", { exact: true })).toHaveCount(5);
  for (const radio of await auditor.getByLabel("No", { exact: true }).all()) await radio.check();
  await auditor.getByRole("button", { name: "Declare independence" }).click();
  await expect(auditor.getByText("Independent", { exact: true })).toBeVisible();

  // The preparer cannot approve their own file; a second reviewer can.
  await auditor.goto(`${AUDITOR_ORIGIN}${audit}/sign-off`);
  await expect(auditor.getByText("Checklist, samples, workpapers, findings and independence are all complete.")).toBeVisible();
  const reviewer = await (await browser.newContext()).newPage();
  await signInAt(reviewer, AUDITOR_ORIGIN, REVIEWER, AUDITOR_PASSWORD, true, "/auditor");
  await reviewer.goto(`${AUDITOR_ORIGIN}${audit}/sign-off`);
  await reviewer.getByLabel("Review note (optional)").fill("Reviewed the synthetic file.");
  await reviewer.getByRole("button", { name: "Approve as second reviewer" }).click();
  await expect(reviewer.getByText("Approved", { exact: false }).first()).toBeVisible();

  // The partner (Quentin) signs by typing their name, then completes the engagement.
  await auditor.reload();
  await auditor.getByLabel("I have reviewed this report and approve the findings in it.").check();
  await auditor.getByLabel("Type your full name to sign").fill("Synthetic Quentin");
  await auditor.getByRole("button", { name: "Sign report" }).click();
  await expect(auditor.getByText("Fingerprint").first()).toBeVisible();
  const fingerprint = (await auditor.locator("code").first().textContent())!.trim();
  expect(fingerprint).toMatch(/^[a-f0-9]{64}$/);
  await auditor.getByRole("button", { name: "Mark complete" }).click();
  await expect(auditor.getByText("Completed", { exact: false }).first()).toBeVisible();

  // The client finds the signed report (no findings) and confirms it.
  const client = await clientPage(browser);
  const portal = portalOrigin(state.slug);
  await client.goto(`${portal}/report`);
  await expect(client.getByText(fingerprint)).toBeVisible();
  await expect(client.getByText(/Finding \d/)).toHaveCount(0);
  await client.getByRole("button", { name: "Confirm I received this report" }).click();
  await expect(client.getByTestId("report-confirmed")).toBeVisible();

  // Only now can an invoice be issued; the client then sees it.
  await auditor.goto(`${AUDITOR_ORIGIN}/auditor/invoices/new`);
  await auditor.getByLabel("Client firm").selectOption({ label: FIRM });
  await auditor.getByLabel("Engagement (optional)").selectOption({ index: 1 });
  await auditor.getByLabel("Issue date").fill(new Date().toISOString().slice(0, 10));
  await auditor.getByLabel("Due date").fill(new Date(Date.now() + 30 * 864e5).toISOString().slice(0, 10));
  await auditor.getByLabel("Description 1").fill("Synthetic Rule 3310 independent test");
  await auditor.getByLabel("Quantity 1").fill("1");
  await auditor.getByLabel(/Rate 1/).fill("1500");
  await auditor.getByRole("button", { name: "Save draft" }).click();
  await auditor.getByRole("button", { name: "Mark sent" }).click();
  await expect(auditor.getByText("Sent", { exact: true }).first()).toBeVisible();
  state.firmId = ((await callApi(auditor, AUDITOR_ORIGIN, `${audit}/summary`)).body as { clientId: string }).clientId;
  await client.goto(`${portal}/invoices`);
  await expect(client.getByText("$1,500.00")).toBeVisible();

  // Isolation: the client cannot read the auditor's sign-off, and the other engagement is unreachable.
  expect((await callApi(client, portal, `${audit}/signoff`)).status).toBe(403);
  expect((await callApi(auditor, AUDITOR_ORIGIN, "/auditor/engagements/synthetic-other-engagement/signoff")).status).toBe(404);
  expect((await callApi(client, portal, "/engagements/synthetic-other-engagement/signed-report")).status).toBe(404);
});

test("7. Quentin runs the isolation check and reads the firm's audit log", async ({ browser }) => {
  const auditor = await auditorPage(browser);
  await auditor.goto(`${AUDITOR_ORIGIN}/auditor/isolation`);
  await auditor.getByRole("button", { name: "Run isolation check" }).click();
  await expect(auditor.getByTestId("isolation-result")).toContainText("Isolation holds");
  await expect(auditor.getByTestId("isolation-id-kind")).toContainText("real engagement of another firm");
  await expect(auditor.getByText("Not refused")).toHaveCount(0);

  await auditor.goto(`${AUDITOR_ORIGIN}/auditor/audit-log`);
  await auditor.getByLabel("Firm").selectOption({ label: FIRM });
  // Step 6 left a trail in this firm's chain, and only this firm's.
  await auditor.getByLabel("Action", { exact: true }).fill("report.confirmed");
  await expect(auditor.getByRole("cell", { name: "report.confirmed" }).first()).toBeVisible();
  await auditor.getByLabel("Action", { exact: true }).fill("signoff.reviewed");
  await expect(auditor.getByRole("cell", { name: "signoff.reviewed" }).first()).toBeVisible();
  await auditor.getByLabel("Action", { exact: true }).fill("");
  await auditor.getByRole("button", { name: "Verify chain" }).click();
  await expect(auditor.getByRole("status").filter({ hasText: "Chain verified" })).toBeVisible();
});
