"use client";

import { useState } from "react";
import { ShieldCheck } from "lucide-react";
import { AuthGate } from "@/components/auth/session";
import { PageHeader } from "@/components/shell/page";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { USE_MOCKS, apiBase } from "@/lib/api";

type Foreign = { engagement: string; firm: string };
type Probe = { label: string; method: "GET" | "POST"; path: (foreign: Foreign) => string; control?: boolean };

const PROBES: Probe[] = [
  { label: "Your own engagements (control, must work)", method: "GET", path: () => "/auditor/engagements", control: true },
  { label: "Read another firm's engagement summary", method: "GET", path: (f) => `/auditor/engagements/${f.engagement}/summary` },
  { label: "Read another firm's checklist conclusions", method: "GET", path: (f) => `/auditor/engagements/${f.engagement}/checklist-tests` },
  { label: "Read another firm's document flags", method: "GET", path: (f) => `/auditor/engagements/${f.engagement}/issues` },
  { label: "Read another firm's report draft", method: "GET", path: (f) => `/auditor/engagements/${f.engagement}/report-draft` },
  { label: "Read another firm's sign-off", method: "GET", path: (f) => `/auditor/engagements/${f.engagement}/signoff` },
  { label: "Read another firm's findings", method: "GET", path: (f) => `/auditor/engagements/${f.engagement}/findings` },
  { label: "Send a checklist to another firm", method: "POST", path: (f) => `/auditor/engagements/${f.engagement}/checklist/send` },
  { label: "Read another firm's audit log", method: "GET", path: (f) => `/auditor/audit-log?firm_id=${f.firm}` },
];

type Result = { label: string; status: number; control: boolean };

/** Step 7: makes real calls with an id that belongs to no firm you are assigned to and shows what the server says. */
export function IsolationProof() {
  const [results, setResults] = useState<Result[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [real, setReal] = useState<boolean | null>(null);
  async function run() {
    setBusy(true);
    // Prefer a real engagement of a firm you are not assigned to (the server hands one back only on
    // the synthetic demo). Without one, fall back to a random id and say so.
    let foreign: Foreign = { engagement: crypto.randomUUID(), firm: crypto.randomUUID() };
    let isReal = false;
    try {
      const r = await fetch(`${apiBase()}/auditor/isolation-probe`, { credentials: "include", cache: "no-store" });
      if (r.ok) {
        const body = (await r.json()) as { foreignEngagementId: string; foreignFirmId: string };
        foreign = { engagement: body.foreignEngagementId, firm: body.foreignFirmId };
        isReal = true;
      }
    } catch { /* keep the random id */ }
    setReal(isReal);
    const out: Result[] = [];
    for (const p of PROBES) {
      let status = 0;
      try {
        const r = await fetch(`${apiBase()}${p.path(foreign)}`, { method: p.method, credentials: "include", cache: "no-store", ...(p.method === "POST" ? { headers: { "Content-Type": "application/json" }, body: "{}" } : {}) });
        status = r.status;
      } catch { status = 0; }
      out.push({ label: p.label, status, control: !!p.control });
    }
    setResults(out);
    setBusy(false);
  }
  const denied = (r: Result) => r.status === 403 || r.status === 404;
  const ok = results ? results.every((r) => (r.control ? r.status === 200 : denied(r))) : false;
  return (
    <AuthGate role="auditor">
      <PageHeader title="Firm isolation proof" description="Every query is scoped by firm. This page asks the server for another firm's data and shows the answer." />
      {USE_MOCKS ? <p className="mb-4 text-sm text-muted">Synthetic demo build: the server is simulated, so this check needs the real backend.</p> : null}
      <Card className="mb-4">
        <CardHeader>
          <CardTitle>Live check</CardTitle>
          <CardDescription>Uses an engagement that belongs to a firm you are not assigned to. The server must refuse every request and must not reveal anything about it.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          <div><Button onClick={() => void run()} disabled={busy || USE_MOCKS}><ShieldCheck aria-hidden className="size-4" /> {busy ? "Checking…" : "Run isolation check"}</Button></div>
          {results ? (
            <>
              <p role="status" className="status-note" data-tone={ok ? "success" : "danger"} data-testid="isolation-result">
                {ok ? "Isolation holds: every foreign request was refused and your own data still loads." : "Isolation check failed. Do not use this build."}
              </p>
              <p className="text-sm text-muted" data-testid="isolation-id-kind">
                {real ? "Tested against a real engagement of another firm in the demo data." : "No second firm is seeded on this server, so a random id was used. That shows the refusal, not a cross-firm denial."}
              </p>
              <Table className="text-left">
                <caption className="sr-only">Isolation checks</caption>
                <THead><TR><TH scope="col">Request</TH><TH scope="col">Server answer</TH><TH scope="col">Result</TH></TR></THead>
                <TBody>
                  {results.map((r) => (
                    <TR key={r.label}>
                      <TD>{r.label}</TD>
                      <TD className="tabular-nums">{r.status || "No answer"}</TD>
                      <TD><Badge variant={(r.control ? r.status === 200 : denied(r)) ? "success" : "danger"}>{r.control ? (r.status === 200 ? "Works" : "Failed") : denied(r) ? "Refused" : "Not refused"}</Badge></TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
            </>
          ) : null}
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Stronger proof in the test suite</CardTitle></CardHeader>
        <CardContent className="text-sm text-muted">
          <p>The browser cannot hold another practice&apos;s real ids. The backend test <code>tests/test_two_practice_isolation.py</code> creates two practices and two firms with marked data, calls every auditor and client route with the other side&apos;s real ids, and checks that nothing is returned or changed. The firm&apos;s audit log is under Audit Log.</p>
        </CardContent>
      </Card>
    </AuthGate>
  );
}
