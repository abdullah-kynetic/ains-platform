"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, CheckCircle2, Clock3, FileText, ShieldCheck } from "lucide-react";
import { AuthGate } from "@/components/auth/session";
import { PageHeader, Stat } from "@/components/shell/page";
import { Button, buttonVariants } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Field } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs } from "@/components/ui/tabs";
import { AuditorWorkspace, ItemCard } from "./workspace";
import { getAuditorQueue, USE_MOCKS, type AuditorQueueItem } from "@/lib/api";
import { syntheticAuditSource, reportReadiness, type AuditWorkspaceData, type ReviewDocument, type ReviewDecision, type ProcessingState } from "@/lib/audit-preview";

const STATE_LABELS: Record<ProcessingState, string> = {
  requested: "Awaiting documents", queued: "Queued", processing: "Processing",
  review: "Ready for auditor", complete: "Auditor reviewed", restricted: "Human handling only", follow_up: "Follow-up not released",
};

function DocumentReview({ document, engagementId, onSave }: { document: ReviewDocument; engagementId: string; onSave: () => void }) {
  const [decision, setDecision] = useState<ReviewDecision>("sufficient");
  const [reason, setReason] = useState("");
  const [tag, setTag] = useState("coverage_verified");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  return <div className="grid gap-4">
    <div className="grid gap-4 lg:grid-cols-2">
      <Card><CardHeader><CardTitle>Document summary</CardTitle></CardHeader><CardContent className="grid gap-3 text-sm">
        <p>{document.summary}</p>
        <div className="rounded-lg border border-border bg-elevated p-3"><p className="mb-1 font-medium">Sufficiency assessment</p><p className="text-muted">{document.assessment}</p></div>
        <p className="text-xs text-subtle">Synthetic analysis · Human review required · Not an audit conclusion</p>
      </CardContent></Card>
      <Card><CardHeader><CardTitle>Source evidence</CardTitle></CardHeader><CardContent className="grid gap-3">
        <p className="flex items-center gap-2 text-sm"><FileText className="size-4" />{document.fileName}</p>
        {document.citations.map((citation, index) => <blockquote key={index} className="border-l-2 border-brand bg-brand-tint/30 p-3 text-sm">
          <p className="mb-2 text-xs font-semibold text-brand-hover">{document.fileName} · Page {citation.page}</p>
          “{citation.quote}”
        </blockquote>)}
        <p className="text-xs text-subtle">This excerpt is fictional preview evidence; no client file is opened or analyzed.</p>
      </CardContent></Card>
    </div>
    <Card><CardHeader><CardTitle>Auditor decision</CardTitle></CardHeader><CardContent className="grid gap-4">
      <p className="text-sm text-muted">Record whether the evidence is sufficient, separately from reviewing a finding. Include business context when correcting the assessment.</p>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Document decision" htmlFor="doc-decision"><Select id="doc-decision" value={decision} onChange={(event) => setDecision(event.target.value as ReviewDecision)}>
          <option value="sufficient">Sufficient for testing</option><option value="more_needed">More evidence needed</option><option value="not_applicable">N/A confirmed by auditor</option>
        </Select></Field>
        <Field label="Review reason category" htmlFor="reason-category"><Select id="reason-category" value={tag} onChange={(event) => setTag(event.target.value)}>
          <option value="coverage_verified">Coverage verified</option><option value="business_context">Business context / no activity</option><option value="wrong_period">Review-period mismatch</option><option value="missing_evidence">Missing evidence</option><option value="analysis_correction">Analysis correction</option>
        </Select></Field>
      </div>
      <Field label="Decision notes" htmlFor="decision-notes" hint="Explain what you checked or why the analysis needs correction."><Textarea id="decision-notes" value={reason} onChange={(event) => setReason(event.target.value)} maxLength={5000} placeholder="For example: No clients were onboarded this month; the representation covers the requested period." /></Field>
      <Button disabled={busy || reason.trim().length < 10} onClick={async () => {
        setBusy(true); setError("");
        try {
          await syntheticAuditSource.review(engagementId, document.id, { decision, reason, tag });
          onSave();
        } catch (caught) { setError(caught instanceof Error ? caught.message : "Could not save decision."); }
        finally { setBusy(false); }
      }}>Save document decision</Button>
      {error ? <p role="alert" className="text-sm text-red-400">{error}</p> : null}
      {document.corrections.length ? <div className="grid gap-2 border-t border-border pt-3"><h4 className="text-sm font-semibold">Review history</h4>{document.corrections.map((entry, index) => <div key={index} className="text-sm">
        <p className="font-medium">{entry.decision.replaceAll("_", " ")} · {entry.tag.replaceAll("_", " ")}</p><p className="text-muted">{entry.reason}</p>
      </div>)}</div> : null}
    </CardContent></Card>
  </div>;
}

function PreviewWorkspace({ engagementId }: { engagementId: string }) {
  const [data, setData] = useState<AuditWorkspaceData | null>(null);
  const [queue, setQueue] = useState<AuditorQueueItem[]>([]);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [selected, setSelected] = useState<string | null>(null);
  const [template, setTemplate] = useState(false);
  async function reload() {
    setData(await syntheticAuditSource.load(engagementId));
    setQueue((await getAuditorQueue()).filter((item) => item.engagementId === engagementId));
  }
  useEffect(() => {
    Promise.all([syntheticAuditSource.load(engagementId), getAuditorQueue()]).then(([workspace, items]) => {
      setData(workspace); setQueue(items.filter((item) => item.engagementId === engagementId));
    }).catch((caught: unknown) => setError(caught instanceof Error ? caught.message : "Could not load workspace."));
  }, [engagementId]);
  if (error) return <p role="alert" className="text-red-400">{error}</p>;
  if (!data) return <Skeleton className="h-80" />;
  const documents = data.documents;
  const received = documents.filter((item) => item.fileName).length;
  const ready = documents.filter((item) => item.state === "review");
  const processing = documents.filter((item) => ["queued", "processing"].includes(item.state));
  const completed = documents.filter((item) => item.state === "complete").length;
  const readiness = reportReadiness(documents);
  const pendingFindings = queue.flatMap((item) => item.findings).filter((finding) => finding.reviewState === "pending").length;
  const pendingNA = queue.filter((item) => item.naReviewState === "pending").length;
  const blockers = readiness.unresolved.length + readiness.restricted.length + readiness.followUps.length + pendingFindings + pendingNA;
  const active = documents.find((item) => item.id === selected);
  const feedback = documents.flatMap((item) => item.corrections.map((correction) => ({ itemId: item.id, title: item.title, ...correction })));
  const visible = documents.filter((item) => (filter === "all" || item.state === filter) && `${item.id} ${item.title} ${item.fileName ?? ""}`.toLowerCase().includes(search.toLowerCase()));
  const documentList = <div className="grid gap-3">
    <div className="flex flex-col gap-3 sm:flex-row"><Input aria-label="Search documents" placeholder="Search request, document, or ID…" value={search} onChange={(event) => setSearch(event.target.value)} />
      <Select aria-label="Filter document status" value={filter} onChange={(event) => setFilter(event.target.value)}><option value="all">All 34 requests</option>{Object.entries(STATE_LABELS).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</Select></div>
    {visible.length ? visible.map((item) => <Card key={item.id}><CardContent className="flex flex-wrap items-center justify-between gap-3 pt-5">
      <div className="min-w-0"><p className="text-xs text-subtle">{item.id} · {item.section}</p><p className="mt-1 text-sm font-medium">{item.title}</p><p className="mt-1 text-xs text-muted">{item.fileName ?? "No file uploaded"}</p></div>
      <div className="flex flex-wrap items-center gap-2"><Badge variant={item.state === "complete" ? "success" : item.state === "restricted" ? "danger" : "default"}>{STATE_LABELS[item.state]}</Badge>
        {item.summary ? <Button variant="outline" size="sm" onClick={() => setSelected(item.id)}>Review document</Button> : null}</div>
    </CardContent></Card>) : <Card><CardContent className="pt-5 text-sm text-muted">No documents match these filters.</CardContent></Card>}
  </div>;
  return <>
    <Link href="/auditor" className={buttonVariants({ variant: "link" })}>← All clients</Link>
    <PageHeader title={data.firmName} description={`Independent AML test · ${data.reviewPeriod.start} to ${data.reviewPeriod.end}`}
      actions={<Link href="/auditor/manage" className={buttonVariants({ variant: "outline" })}>Engagement setup</Link>} />
    <Tabs onValueChange={() => setSelected(null)} items={[
      { value: "dashboard", label: "Dashboard", content: <div className="grid gap-5">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4"><Stat label="Documents received" value={received} hint="Across 34 master requests" /><Stat label="Queued / processing" value={processing.length} /><Stat label="Awaiting your review" value={ready.length} /><Stat label="Auditor reviewed" value={completed} /></div>
        <Card featured><CardHeader><CardTitle>Engagement progress</CardTitle></CardHeader><CardContent className="grid gap-3"><Progress value={completed / documents.length * 100} /><p className="text-sm text-muted">{completed} of {documents.length} requests reviewed by the auditor</p>
          <div className="grid gap-3 sm:grid-cols-4">{[{ icon: FileText, title: "Collect documents", sub: `${received} received` }, { icon: Clock3, title: "Analyze evidence", sub: `${processing.length} in pipeline` }, { icon: ShieldCheck, title: "Auditor review", sub: `${ready.length} ready` }, { icon: CheckCircle2, title: "Draft report", sub: `${blockers} unresolved` }].map((stage) => <div key={stage.title} className="rounded-lg border border-border p-3"><stage.icon className="mb-2 size-4 text-brand-hover" /><p className="text-sm font-medium">{stage.title}</p><p className="mt-1 text-xs text-muted">{stage.sub}</p></div>)}</div>
        </CardContent></Card>
        <div className="grid gap-4 lg:grid-cols-2"><Card><CardHeader><CardTitle>Ready for your attention</CardTitle></CardHeader><CardContent className="grid gap-3">{ready.length ? ready.map((item) => <Button key={item.id} variant="outline" className="h-auto justify-between whitespace-normal py-3 text-left" onClick={() => setSelected(item.id)}>{item.title}<ArrowRight /></Button>) : <p className="text-sm text-muted">No documents awaiting review.</p>}</CardContent></Card>
          <Card><CardHeader><CardTitle>Collection by section</CardTitle></CardHeader><CardContent className="grid gap-3">{Array.from(new Set(documents.map((item) => item.section))).map((section) => {
            const entries = documents.filter((item) => item.section === section); const count = entries.filter((item) => item.fileName).length;
            return <div key={section}><div className="mb-1 flex justify-between text-xs"><span>{section}</span><span>{count}/{entries.length}</span></div><Progress value={count / entries.length * 100} /></div>;
          })}</CardContent></Card></div>
      </div> },
      { value: "documents", label: "Documents", content: documentList },
      { value: "processing", label: `AI processing (${processing.length})`, content: <div className="grid gap-3"><p className="text-sm text-muted">Stages and elapsed times below are synthetic examples. No live model is connected.</p>{processing.map((item) => <Card key={item.id}><CardContent className="flex flex-wrap justify-between gap-3 pt-5"><div><p className="text-sm font-medium">{item.title}</p><p className="mt-1 text-xs text-muted">{item.fileName}</p></div><div><Badge variant="info">{STATE_LABELS[item.state]}</Badge><p className="mt-2 text-xs text-muted">{item.stage}{item.elapsedSeconds !== null ? ` · ${item.elapsedSeconds}s elapsed` : ""}</p></div></CardContent></Card>)}{!processing.length ? <p className="text-sm text-muted">No documents queued or processing.</p> : null}</div> },
      { value: "review", label: "Auditor review", content: <div className="grid gap-5"><h2 className="text-lg font-semibold">Document assessments</h2>{ready.length ? ready.map((item) => <Button key={item.id} variant="outline" className="h-auto whitespace-normal py-3" onClick={() => setSelected(item.id)}>{item.title} — review assessment</Button>) : <p className="text-sm text-muted">All available assessments have been reviewed.</p>}
        <h2 className="text-lg font-semibold">Finding and N/A decisions</h2>{queue.map((item) => <ItemCard key={item.itemId} item={item} onChanged={reload} />)}</div> },
      { value: "feedback", label: "Review feedback", content: <div className="grid gap-3">
        <PageHeader title="Review feedback" description="Recorded auditor decisions and corrections for later evaluation. These notes do not automatically retrain or change an AI model." actions={<Button variant="outline" disabled={!feedback.length} onClick={() => {
          const href = URL.createObjectURL(new Blob([JSON.stringify({ synthetic: true, engagementId, feedback }, null, 2)], { type: "application/json" }));
          const link = window.document.createElement("a"); link.href = href; link.download = "synthetic-review-feedback.json"; link.click(); URL.revokeObjectURL(href);
        }}>Export review notes</Button>} />
        {feedback.length ? feedback.map((entry, index) => <Card key={`${entry.itemId}-${index}`}><CardContent className="grid gap-2 pt-5"><div className="flex flex-wrap justify-between gap-2"><p className="text-sm font-medium">{entry.itemId} · {entry.title}</p><Badge>{entry.tag.replaceAll("_", " ")}</Badge></div><p className="text-sm text-muted">{entry.reason}</p><p className="text-xs text-subtle">{entry.decision.replaceAll("_", " ")} · {new Date(entry.at).toLocaleString()}</p></CardContent></Card>) : <p className="text-sm text-muted">No review notes recorded yet.</p>}
      </div> },
      { value: "report", label: "Report readiness", content: <div className="grid gap-4">
        <Card><CardHeader><CardTitle>Review completion required</CardTitle></CardHeader><CardContent className="grid gap-3"><p className="text-sm text-muted">{completed} reviewed · {readiness.unresolved.length} unresolved document requests · {readiness.restricted.length} human-handled requests · {readiness.followUps.length} unreleased follow-up · {pendingFindings} pending findings · {pendingNA} pending N/A decisions</p>
          <p className="text-sm">All applicable requests, findings, N/A decisions, and restricted handling must be resolved before a final draft is ready. Quinton signs the report.</p><div className="flex flex-wrap gap-2"><Button disabled title="Outstanding review decisions and live report integration are required">Generate draft report</Button><Button variant="outline" onClick={() => setTemplate(!template)}>Preview report layout</Button></div>
        </CardContent></Card>
        {template ? <Card><CardContent className="grid gap-3 pt-5"><Badge variant="warning">SYNTHETIC LAYOUT PREVIEW · UNSIGNED</Badge><h2 className="text-xl font-semibold">Independent AML Test — Draft Report</h2><p>{data.firmName}</p><p className="text-sm text-muted">Scope and review period · Executive summary · Testing performed · Approved findings and evidence citations · Management responses · Auditor signature</p><p className="text-sm">This previews the report structure only. It is not a generated audit report.</p></CardContent></Card> : null}
      </div> },
    ]} />
    {active ? <section className="mt-6 border-t border-border pt-6" aria-label="Selected document review"><div className="mb-4 flex items-start justify-between gap-3"><div><p className="text-xs text-subtle">{active.id}</p><h2 className="text-lg font-semibold">{active.title}</h2></div><Button variant="ghost" onClick={() => setSelected(null)}>Close review</Button></div><DocumentReview key={active.id} document={active} engagementId={engagementId} onSave={() => void reload()} /></section> : null}
  </>;
}

export function EngagementWorkspace({ engagementId }: { engagementId: string }) {
  return <AuthGate role="auditor">{USE_MOCKS ? <PreviewWorkspace engagementId={engagementId} /> : <AuditorWorkspace engagementId={engagementId} />}</AuthGate>;
}
