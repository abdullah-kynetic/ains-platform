"use client";

import { useState } from "react";
import { Download, FileText, MessageSquareReply, Printer, Receipt } from "lucide-react";
import { AuthGate } from "@/components/auth/session";
import { PageHeader } from "@/components/shell/page";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/label";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { downloadWord, listResponseRequests, listPortalInvoices, listPortalReports, respondToRequest, type ResponseRequest } from "@/lib/api/index";
import { Loading, MockNotice, fmtDate, money, useAsync } from "@/components/auditor/kit";

function ResponseForm({ request, onDone }: { request: ResponseRequest; onDone: () => void }) {
  const [text, setText] = useState("");
  const [problem, setProblem] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <form className="grid gap-3 border-t border-border pt-4" onSubmit={async (e) => { e.preventDefault(); setBusy(true); setProblem(""); try { await respondToRequest(request.id, text); onDone(); } catch (err) { setProblem((err as Error).message); } finally { setBusy(false); } }}>
      <Field label="Your response" hint="Say what you will do and by when."><Textarea value={text} onChange={(e) => setText(e.target.value)} /></Field>
      {problem && <p role="alert" className="status-note" data-tone="warning">{problem}</p>}
      <div><Button type="submit" disabled={busy || !text.trim()}>Submit response</Button></div>
    </form>
  );
}

export function PortalResponses() {
  const { data, error, reload } = useAsync(listResponseRequests, []);
  return (
    <AuthGate role="client">
      <PageHeader title="Responses requested" description="Items your auditor has asked you to respond to. Reply to each one." />
      <MockNotice />
      {!data ? <Loading error={error} retry={reload} label="Loading requests…" /> : data.length === 0 ? (
        <EmptyState icon={MessageSquareReply} title="Nothing needs a response" description="When your auditor asks for a response, it will appear here." />
      ) : (
        <div className="grid gap-3">
          {data.map((r) => (
            <Card key={r.id}>
              <CardHeader className="flex-row flex-wrap items-start justify-between gap-2"><CardTitle>{r.title}</CardTitle>{r.status === "open" ? <Badge variant="deadline">Response needed</Badge> : <Badge variant="brand">Response sent</Badge>}</CardHeader>
              <CardContent className="grid gap-3 text-sm">
                <p>{r.requestText}</p>
                {r.status === "responded" ? <div className="rounded-lg bg-elevated p-3"><p className="text-xs font-medium text-muted">Your response · {fmtDate(r.respondedAt)}</p><p className="mt-1">{r.response}</p></div> : <ResponseForm request={r} onDone={reload} />}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </AuthGate>
  );
}

export function PortalReport() {
  const { data, error, reload } = useAsync(listPortalReports, []);
  return (
    <AuthGate role="client">
      <PageHeader title="Report" description="Signed reports from your auditor. A report appears once the partner has signed it." />
      <MockNotice />
      {!data ? <Loading error={error} retry={reload} label="Loading reports…" /> : (
        <div className="grid gap-4">
          {data.map((r) => r.available ? (
            <Card key={r.id}>
              <CardHeader className="flex-row flex-wrap items-center justify-between gap-2"><CardTitle>AML independent test, {r.period}</CardTitle><div className="flex gap-2"><Button size="sm" variant="outline" onClick={() => downloadWord(`AML independent test ${r.period}`, r.sections, r.fingerprint)}><Download aria-hidden />Word</Button><Button size="sm" variant="outline" onClick={() => window.print()}><Printer aria-hidden />PDF</Button></div></CardHeader>
              <CardContent className="report-print-area grid gap-4">
                <p className="text-sm text-muted">Signed by {r.signedBy} on {fmtDate(r.signedOn)}. Fingerprint <code className="break-all text-xs">{r.fingerprint}</code></p>
                {r.sections.map((s) => <div key={s.id}><h3 className="text-sm font-semibold">{s.title}</h3><p className="text-sm leading-relaxed">{s.body}</p></div>)}
              </CardContent>
            </Card>
          ) : (
            <EmptyState key={r.id} icon={FileText} title={`${r.period} report not signed yet`} description="You will get an email when it is ready. It will appear here." />
          ))}
        </div>
      )}
    </AuthGate>
  );
}

export function PortalInvoices() {
  const { data, error, reload } = useAsync(listPortalInvoices, []);
  const label = { sent: ["brand", "Sent"], paid: ["success", "Paid"], overdue: ["warning", "Overdue"] } as const;
  return (
    <AuthGate role="client">
      <PageHeader title="Invoices" description="Invoices for your engagements. To pay, use the instructions on the invoice or contact your auditor." />
      <MockNotice />
      {!data ? <Loading error={error} retry={reload} label="Loading invoices…" /> : data.length === 0 ? (
        <EmptyState icon={Receipt} title="No invoices yet" description="Invoices from your auditor will appear here." />
      ) : (
        <Table>
          <THead><TR><TH>Invoice</TH><TH>Issued</TH><TH>Due</TH><TH>Amount</TH><TH>Status</TH></TR></THead>
          <TBody>{data.map((i) => <TR key={i.id}><TD className="font-medium">{i.number}</TD><TD>{fmtDate(i.issued)}</TD><TD>{fmtDate(i.due)}</TD><TD className="tabular-nums">{money(i.amountCents)}</TD><TD><Badge variant={label[i.status][0]}>{label[i.status][1]}</Badge></TD></TR>)}</TBody>
        </Table>
      )}
    </AuthGate>
  );
}
