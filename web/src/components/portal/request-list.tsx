"use client";

import { useCallback, useEffect, useState } from "react";
import { FileText, ListChecks } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress as Bar } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";
import { LoadState } from "@/components/ui/load-state";
import { getProgress, ITEM_LABEL, listEngagementDocuments, requestNA, type DocRef, type ItemState, type Progress, type ProgressItem } from "@/lib/api/flow";

const tone: Record<ItemState, "default" | "brand" | "success" | "warning" | "info"> = {
  not_started: "default",
  submitted: "info",
  needs_info: "warning",
  accepted: "success",
  na: "default",
  restricted: "default",
};

/** The client's numbered checklist on the real workflow routes (steps 3 and 4). */
export function RequestList({ engagementId }: { engagementId: string }) {
  const [progress, setProgress] = useState<Progress | null>(null);
  const [documents, setDocuments] = useState<DocRef[]>([]);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const load = useCallback(() => {
    Promise.all([getProgress(engagementId, "client"), listEngagementDocuments()])
      .then(([p, docs]) => { setProgress(p); setDocuments(docs); })
      .catch((e: Error) => setError(e.message));
  }, [engagementId]);
  useEffect(load, [load]);
  if (!progress) return <LoadState error={error || null} retry={load} />;
  const open = !!progress.checklistSentAt;
  const feedback = new Map(documents.map((d) => [d.id, d.feedback]));
  const shown = progress.items
    .map((i) => ({ ...i, documents: i.documents.map((d) => ({ ...d, feedback: d.feedback ?? feedback.get(d.id) ?? null })) }))
    .filter((i) => `${i.number} ${i.requestId} ${i.title}`.toLowerCase().includes(search.toLowerCase()));
  const active = shown.filter((i) => i.status !== "na");
  const na = shown.filter((i) => i.status === "na");
  return (
    <div className="grid gap-4" data-testid="request-list">
      <div className="grid gap-[var(--space-3)] rounded-xl border border-border bg-card p-4 shadow-card">
        <div className="flex flex-wrap justify-between gap-2 text-sm">
          <span className="font-medium">Document collection</span>
          <span className="text-muted" data-testid="request-progress">
            {progress.counts.submitted + progress.counts.accepted + progress.counts.notApplicable} of {progress.counts.total} requests with your auditor or N/A
          </span>
        </div>
        <Bar value={progress.percentSubmitted} />
      </div>
      <label className="grid max-w-xl gap-2 text-sm font-medium">
        Search document requests
        <Input placeholder="Number, request ID or title" value={search} onChange={(event) => setSearch(event.target.value)} />
      </label>
      {!shown.length ? (
        <EmptyState icon={ListChecks} title="No matching requests" description="Try a different request number or title." />
      ) : null}
      {[{ id: "active", title: "Document requests", rows: active }, { id: "na", title: "Does not apply", rows: na }]
        .filter((s) => s.rows.length)
        .map((section) => (
          <details open key={section.id} className="rounded-xl border border-border bg-card p-4 shadow-card" data-testid={`section-${section.id}`}>
            <summary className="cursor-pointer text-base font-medium">
              {section.title}
              <span className="ml-3 text-xs font-normal text-muted">{section.rows.length} request{section.rows.length === 1 ? "" : "s"}</span>
            </summary>
            <div className="mt-3">
              {section.rows.map((item) => (
                <RequestRow key={item.id} item={item} engagementId={engagementId} open={open} onChanged={load} />
              ))}
            </div>
          </details>
        ))}
    </div>
  );
}

function RequestRow({ item, engagementId, open, onChanged }: { item: ProgressItem; engagementId: string; open: boolean; onChanged: () => void }) {
  const [asking, setAsking] = useState(false);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const pending = item.naRequest?.state === "pending";
  const canAsk = open && !pending && item.status !== "na" && item.status !== "restricted" && item.status !== "accepted";

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await action();
      onChanged();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save this request.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-2 border-t border-border py-4 first:border-t-0" data-testid={`request-${item.requestId}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-mono text-xs text-brand-hover">{item.number}. {item.requestId}</p>
          <p className="content-heading text-sm font-medium">{item.title}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={tone[item.status]}>{ITEM_LABEL[item.status]}</Badge>
          {canAsk && !asking ? (
            <Button variant="outline" size="sm" onClick={() => setAsking(true)} aria-label={`Does not apply: ${item.requestId}`}>
              Does not apply
            </Button>
          ) : null}
        </div>
      </div>
      {item.documents.length ? (
        <ul className="flex flex-wrap gap-2 text-xs text-muted" aria-label={`Documents for ${item.requestId}`}>
          {item.documents.map((d) => (
            <li key={d.id} className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-0.5">
              <FileText aria-hidden className="size-3.5" /> <span className="font-mono">{d.number}</span> {d.name}
              {d.feedback ? <span className="text-warning-foreground">· {d.feedback}</span> : null}
            </li>
          ))}
        </ul>
      ) : null}
      {pending ? <p className="text-sm text-muted">N/A requested: “{item.naRequest!.reason}”. Waiting for your auditor.</p> : null}
      {item.naRequest?.state === "rejected" ? (
        <p className="status-note" data-tone="warning">Your auditor needs this request: {item.naRequest.decisionNote}</p>
      ) : null}
      {item.status === "na" && item.naRequest?.reason ? <p className="text-xs text-muted">Accepted as not applicable: “{item.naRequest.reason}”</p> : null}
      {item.status === "na" && !item.naRequest?.reason ? <p className="text-xs text-muted">Marked N/A by client in the questionnaire, or by your auditor.</p> : null}
      {asking ? (
        <form
          className="grid gap-2"
          onSubmit={(event) => { event.preventDefault(); void run(async () => { await requestNA(engagementId, item.id, reason.trim()); setAsking(false); setReason(""); }); }}
        >
          <label className="grid gap-1 text-sm font-medium" htmlFor={`na-${item.id}`}>
            Why does {item.requestId} not apply to your firm?
            <Textarea id={`na-${item.id}`} value={reason} onChange={(e) => setReason(e.target.value)} minLength={5} maxLength={1000} required />
          </label>
          <div className="flex gap-2">
            <Button type="submit" size="sm" disabled={busy || reason.trim().length < 5}>{busy ? "Sending…" : "Send to auditor"}</Button>
            <Button type="button" size="sm" variant="ghost" onClick={() => setAsking(false)}>Cancel</Button>
          </div>
        </form>
      ) : null}
      {error ? <p role="alert" className="text-sm text-warning-foreground">{error}</p> : null}
    </div>
  );
}
