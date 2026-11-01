"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AuthGate } from "@/components/auth/session";
import { PageHeader } from "@/components/shell/page";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import {
  downloadDraftReport,
  getAuditorQueue,
  reviewFinding,
  reviewNotApplicable,
  type AuditorFinding,
  type AuditorQueueItem,
} from "@/lib/api";

function FindingEditor({ finding, onUpdated }: { finding: AuditorFinding; onUpdated: (finding: AuditorFinding) => void }) {
  const [body, setBody] = useState(finding.body);
  const [severity, setSeverity] = useState(finding.severity);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function decide(action: "accept" | "edit" | "reject") {
    setBusy(true);
    setError("");
    try {
      const updated = await reviewFinding(finding.id, {
        action,
        ...(action === "edit" ? { body, severity, citations: finding.citations } : {}),
        ...(action === "accept" ? { severity } : {}),
      });
      onUpdated(updated);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save this decision.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-3 rounded-lg border border-border bg-elevated/50 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="font-medium">{finding.title}</div>
        <Badge variant={finding.reviewState === "rejected" ? "danger" : finding.reviewState === "pending" ? "warning" : "success"}>{finding.reviewState}</Badge>
      </div>
      <Field label="Finding draft">
        <Textarea value={body} onChange={(event) => setBody(event.target.value)} />
      </Field>
      <Field label="Severity">
        <Select value={severity} onChange={(event) => setSeverity(event.target.value as AuditorFinding["severity"])}>
          <option value="low">Low</option>
          <option value="moderate">Moderate</option>
          <option value="high">High</option>
          <option value="critical">Critical</option>
        </Select>
      </Field>
      <div>
        <p className="mb-1 text-xs font-medium uppercase tracking-wide text-subtle">Evidence citations</p>
        {finding.citations.length ? finding.citations.map((citation, index) => (
          <p key={`${citation.page}-${index}`} className="text-sm text-muted">Page {citation.page}: “{citation.quote}”</p>
        )) : <p className="status-note text-sm" data-tone="danger">A page citation is required before approval.</p>}
      </div>
      <div className="flex flex-wrap gap-2">
        <Button size="sm" disabled={busy || !finding.citations.length} onClick={() => void decide("accept")}>Accept</Button>
        <Button size="sm" variant="secondary" disabled={busy || !finding.citations.length || !body.trim()} onClick={() => void decide("edit")}>Save edited</Button>
        <Button size="sm" variant="destructive" disabled={busy} onClick={() => void decide("reject")}>Reject</Button>
      </div>
      {error ? <p className="status-note" data-tone="danger">{error}</p> : null}
    </div>
  );
}

function ItemCard({ item, onChanged }: { item: AuditorQueueItem; onChanged: () => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function decideNA(decision: "approve" | "reject") {
    setBusy(true);
    setError("");
    try {
      await reviewNotApplicable(item.engagementId, item.itemId, decision);
      await onChanged();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not review this N/A answer.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle>{item.itemTitle}</CardTitle>
          <Badge>{item.clientStatus.replaceAll("_", " ")}</Badge>
        </div>
        <CardDescription>{item.firmName}</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        {item.naReviewState === "pending" ? (
          <div className="rounded-lg border border-warning/30 bg-warning/5 p-4">
            <p className="text-sm text-foreground">The firm answered that this item does not apply. Quentin must approve or reject that answer.</p>
            <div className="mt-3 flex gap-2">
              <Button size="sm" disabled={busy} onClick={() => void decideNA("approve")}>Approve N/A</Button>
              <Button size="sm" variant="destructive" disabled={busy} onClick={() => void decideNA("reject")}>Reject N/A</Button>
            </div>
          </div>
        ) : null}

        <section>
          <h3 className="mb-2 text-sm font-semibold">Evidence and automated checks</h3>
          {item.evidence.length ? item.evidence.map((evidence) => (
            <div key={evidence.id} className="mb-2 rounded-lg border border-border p-3 text-sm">
              <div className="font-medium">{evidence.name}</div>
              <div className="mt-1 break-all text-xs text-subtle">SHA-256 {evidence.sha256} · version {evidence.version}</div>
              <div className="mt-2 grid gap-1">
                {evidence.checks.map((check) => (
                  <div key={check.id} className="flex items-center justify-between gap-2 text-muted">
                    <span>{check.checkType.replaceAll("_", " ")}</span><Badge variant={check.status === "passed" ? "success" : "warning"}>{check.status}</Badge>
                  </div>
                ))}
              </div>
            </div>
          )) : <p className="text-sm text-muted">No uploaded evidence for this item.</p>}
        </section>

        <section>
          <h3 className="mb-2 text-sm font-semibold">Internal finding drafts</h3>
          <div className="grid gap-3">
            {item.findings.length ? item.findings.map((finding) => (
              <FindingEditor key={finding.id} finding={finding} onUpdated={() => void onChanged()} />
            )) : <p className="text-sm text-muted">No finding drafts.</p>}
          </div>
        </section>
        {error ? <p className="status-note" data-tone="danger">{error}</p> : null}
      </CardContent>
    </Card>
  );
}

export function AuditorWorkspace({ engagementId }: { engagementId?: string }) {
  const [items, setItems] = useState<AuditorQueueItem[] | null>(null);
  const [error, setError] = useState("");
  const [reportBusy, setReportBusy] = useState(false);

  async function load() {
    try {
      setItems(await getAuditorQueue());
      setError("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not load the review queue.");
    }
  }

  useEffect(() => {
    getAuditorQueue().then(setItems).catch((caught: unknown) => {
      setError(caught instanceof Error ? caught.message : "Could not load the review queue.");
    });
  }, []);

  const visible = (items ?? []).filter((item) => !engagementId || item.engagementId === engagementId);
  const engagements = Array.from(new Map((items ?? []).map((item) => [item.engagementId, item])).values());

  async function report(format: "docx" | "pdf") {
    if (!engagementId) return;
    setReportBusy(true);
    setError("");
    try {
      await downloadDraftReport(engagementId, format);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not generate the draft report.");
    } finally {
      setReportBusy(false);
    }
  }

  return (
    <AuthGate role="auditor">
      <PageHeader
        title={engagementId ? (visible[0]?.firmName ?? "Engagement review") : "Quentin’s review queue"}
        description="Internal evidence, automated checks, and finding drafts. Nothing on this page is shown to clients."
        actions={engagementId ? (
          <div className="flex gap-2">
            <Button variant="outline" disabled={reportBusy} onClick={() => void report("docx")}>Draft DOCX</Button>
            <Button variant="outline" disabled={reportBusy} onClick={() => void report("pdf")}>Draft PDF</Button>
          </div>
        ) : undefined}
      />
      {error ? <p className="status-note mb-[var(--space-4)]" data-tone="danger">{error}</p> : null}
      {!items ? <Skeleton className="h-72 w-full" /> : engagementId ? (
        <div className="grid gap-4">
          <Link href="/auditor" className={buttonVariants({ variant: "link" })}>← Back to queue</Link>
          {visible.length ? visible.map((item) => <ItemCard key={item.itemId} item={item} onChanged={load} />) : <Card><CardContent className="pt-5 text-sm text-muted">No pending work for this engagement.</CardContent></Card>}
        </div>
      ) : (
        <div className="grid gap-4">
          {engagements.length ? engagements.map((engagement) => {
            const count = (items ?? []).filter((item) => item.engagementId === engagement.engagementId).length;
            return (
              <Card key={engagement.engagementId}>
                <CardHeader><CardTitle>{engagement.firmName}</CardTitle><CardDescription>{count} item{count === 1 ? "" : "s"} awaiting review</CardDescription></CardHeader>
                <CardContent><Link className={buttonVariants()} href={`/auditor/engagements/${engagement.engagementId}`}>Open engagement</Link></CardContent>
              </Card>
            );
          }) : <Card><CardContent className="pt-5 text-sm text-muted">The review queue is clear.</CardContent></Card>}
        </div>
      )}
    </AuthGate>
  );
}
