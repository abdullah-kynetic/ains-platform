"use client";

import { useState } from "react";
import { Send } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress as Bar } from "@/components/ui/progress";
import { acceptItem, decideNA, getProgress, ITEM_LABEL, sendChecklist, STAGE_LABEL, type ProgressItem } from "@/lib/api/flow";
import { Textarea } from "@/components/ui/textarea";
import { Loading, fmtDateTime, useAsync } from "../kit";

/** Step 2: send the numbered checklist to the client and watch collection progress. */
export function ClientChecklistCard({ id }: { id: string }) {
  const { data, error, reload } = useAsync(() => getProgress(id, "auditor"), [id]);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState("");

  async function send() {
    setBusy(true);
    setFailure("");
    try {
      await sendChecklist(id);
      reload();
    } catch (caught) {
      setFailure(caught instanceof Error ? caught.message : "Could not send the checklist.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="mb-4" data-testid="client-checklist-card">
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle>Client checklist</CardTitle>
          <CardDescription>
            {data?.checklistSentAt
              ? `Sent ${fmtDateTime(data.checklistSentAt)}. The client sees the numbered requests 1 to ${data.items.length}.`
              : "The client cannot start until you send the numbered checklist."}
          </CardDescription>
        </div>
        <div className="flex items-center gap-2">
          {data ? <Badge variant="brand" data-testid="workflow-stage">{STAGE_LABEL[data.stage]}</Badge> : null}
          {data && !data.checklistSentAt ? (
            <Button onClick={() => void send()} disabled={busy}>
              <Send aria-hidden className="size-4" /> {busy ? "Sending…" : "Send checklist to client"}
            </Button>
          ) : null}
        </div>
      </CardHeader>
      <CardContent>
        {error ? <p role="alert" className="status-note" data-tone="danger">{error}</p> : null}
        {failure ? <p role="alert" className="status-note" data-tone="danger">{failure}</p> : null}
        {data ? (
          <div className="grid gap-2 text-sm">
            <div className="flex flex-wrap justify-between gap-2 text-muted">
              <span>{data.percentSubmitted}% submitted · {data.percentAccepted}% accepted for testing</span>
              <span className="tabular-nums">
                {data.counts.notStarted} not started · {data.counts.submitted} with you · {data.counts.needsInfo} need information · {data.counts.notApplicable} N/A
                {data.counts.naPending ? ` · ${data.counts.naPending} N/A requests to decide` : ""}
              </span>
            </div>
            <Bar value={data.percentSubmitted} />
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

/** Steps 3 to 5: the client's items as the server sees them, with Quentin's decisions. */
export function ClientItemsPanel({ id }: { id: string }) {
  const { data, error, reload } = useAsync(() => getProgress(id, "auditor"), [id]);
  if (!data) return <Loading error={error} retry={reload} label="Loading client checklist…" />;
  const pending = data.items.filter((i) => i.naRequest?.state === "pending");
  return (
    <div className="grid gap-4" data-testid="client-items">
      <ClientChecklistCard id={id} />
      <Card>
        <CardHeader>
          <CardTitle>N/A requests to decide</CardTitle>
          <CardDescription>The client asked for these to be marked not applicable. Only you decide.</CardDescription>
        </CardHeader>
        <CardContent>
          {pending.length === 0 ? <p className="text-sm text-muted">No N/A requests waiting.</p> : (
            <ul className="grid gap-4">
              {pending.map((item) => <NADecisionRow key={item.id} engagementId={id} item={item} onDone={reload} />)}
            </ul>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>All requests</CardTitle></CardHeader>
        <CardContent>
          <ul className="divide-y divide-border text-sm">
            {data.items.map((item) => (
              <li key={item.id} className="flex flex-wrap items-center justify-between gap-2 py-2" data-testid={`client-item-${item.requestId}`}>
                <span><span className="font-mono text-xs text-brand-hover">{item.number}. {item.requestId}</span> {item.title}</span>
                <span className="flex flex-wrap items-center gap-2">
                  {item.documents.map((d) => <Badge key={d.id} variant="default">{d.number}</Badge>)}
                  {item.naRequest?.state === "rejected" ? <Badge variant="warning">N/A rejected</Badge> : null}
                  <Badge variant={item.status === "needs_info" ? "warning" : item.status === "accepted" ? "success" : "brand"}>{ITEM_LABEL[item.status]}</Badge>
                  {item.status === "submitted" && item.openIssues === 0 ? <AcceptButton engagementId={id} item={item} onDone={reload} /> : null}
                </span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}

function NADecisionRow({ engagementId, item, onDone }: { engagementId: string; item: ProgressItem; onDone: () => void }) {
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function decide(decision: "accept" | "reject") {
    setBusy(true);
    setError("");
    try {
      await decideNA(engagementId, item.id, decision, note.trim() || undefined);
      onDone();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not record the decision.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <li className="grid gap-2" data-testid={`na-request-${item.requestId}`}>
      <p className="text-sm"><span className="font-mono text-xs text-brand-hover">{item.number}. {item.requestId}</span> {item.title}</p>
      <p className="text-sm text-muted">Client’s reason: “{item.naRequest?.reason}”</p>
      <label className="grid gap-1 text-sm font-medium" htmlFor={`decision-${item.id}`}>
        Note to the client (required to reject)
        <Textarea id={`decision-${item.id}`} value={note} onChange={(e) => setNote(e.target.value)} maxLength={1000} className="min-h-16" />
      </label>
      <div className="flex gap-2">
        <Button size="sm" onClick={() => void decide("accept")} disabled={busy}>Approve N/A</Button>
        <Button size="sm" variant="outline" onClick={() => void decide("reject")} disabled={busy || !note.trim()}>Reject</Button>
      </div>
      {error ? <p role="alert" className="text-sm text-warning-foreground">{error}</p> : null}
    </li>
  );
}

function AcceptButton({ engagementId, item, onDone }: { engagementId: string; item: ProgressItem; onDone: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  return (
    <>
      <Button size="sm" variant="outline" disabled={busy} aria-label={`Accept ${item.requestId} for testing`}
        onClick={() => { setBusy(true); setError(""); acceptItem(engagementId, item.id).then(onDone).catch((e: Error) => setError(e.message)).finally(() => setBusy(false)); }}>
        Accept for testing
      </Button>
      {error ? <span role="alert" className="text-xs text-warning-foreground">{error}</span> : null}
    </>
  );
}
