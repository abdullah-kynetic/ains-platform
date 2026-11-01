"use client";

import { useState } from "react";
import { FileWarning, Plus, Trash2 } from "lucide-react";
import { PageHeader } from "@/components/shell/page";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { deleteDraftFinding, findingBlockers, listDocuments, listFindings, saveFinding, setFindingStatus, type Citation, type Finding, type FindingInput, type Severity } from "@/lib/api/index";
import { FindingStatusBadge, Loading, MockNotice, SeverityBadge, fmtDate, useAsync } from "../kit";

const RULES = ["FINRA Rule 3310(a): risk-based AML program", "FINRA Rule 3310(b): suspicious activity detection and reporting", "FINRA Rule 3310(c): independent testing", "FINRA Rule 3310(d): AML compliance person", "FINRA Rule 3310(e): ongoing training", "BSA: Customer Identification Program pillar", "BSA: Customer due diligence pillar", "BSA: suspicious activity monitoring pillar", "BSA: OFAC / sanctions screening"];
const empty = (): FindingInput => ({ engagementId: "", title: "", rule: "", condition: "", cause: "", effect: "", recommendation: "", severity: "moderate", citations: [] });

function FindingForm({ id, existing, docs, onClose, onSaved }: { id: string; existing?: Finding; docs: string[]; onClose: () => void; onSaved: () => void }) {
  const [f, setF] = useState<FindingInput>(existing ? { ...existing } : empty());
  const [busy, setBusy] = useState(false);
  const set = <K extends keyof FindingInput>(k: K, v: FindingInput[K]) => setF({ ...f, [k]: v });
  const cite = (i: number, patch: Partial<Citation>) => set("citations", f.citations.map((c, j) => (j === i ? { ...c, ...patch } : c)));
  const blockers = findingBlockers(f);
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()} className="max-w-2xl" title={existing ? "Edit finding" : "New finding"} description="Condition, cause, effect and recommendation. Every finding cites a document and page.">
      <form className="grid gap-3" onSubmit={async (e) => { e.preventDefault(); if (!f.title.trim()) return; setBusy(true); await saveFinding(id, f, existing?.id); setBusy(false); onSaved(); onClose(); }}>
        <Field label="Title"><Input value={f.title} onChange={(e) => set("title", e.target.value)} required /></Field>
        <Field label="Rule cited"><Input list="rule-options" value={f.rule} onChange={(e) => set("rule", e.target.value)} placeholder="e.g. FINRA Rule 3310(c)" /><datalist id="rule-options">{RULES.map((r) => <option key={r} value={r} />)}</datalist></Field>
        <Field label="Condition" hint="What we found."><Textarea value={f.condition} onChange={(e) => set("condition", e.target.value)} /></Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Cause"><Textarea value={f.cause} onChange={(e) => set("cause", e.target.value)} /></Field>
          <Field label="Effect"><Textarea value={f.effect} onChange={(e) => set("effect", e.target.value)} /></Field>
        </div>
        <Field label="Recommendation"><Textarea value={f.recommendation} onChange={(e) => set("recommendation", e.target.value)} /></Field>
        <Field label="Severity"><Select value={f.severity} onChange={(e) => set("severity", e.target.value as Severity)}>{(["low", "moderate", "high", "critical"] as const).map((s) => <option key={s} value={s}>{s[0].toUpperCase() + s.slice(1)}</option>)}</Select></Field>
        <fieldset className="grid gap-2">
          <legend className="mb-1 text-sm font-medium">Citations (document and page)</legend>
          {f.citations.map((c, i) => (
            <div key={i} className="flex gap-2">
              <div className="min-w-0 flex-1"><Select aria-label={`Citation ${i + 1} document`} value={c.document} onChange={(e) => cite(i, { document: e.target.value })}><option value="">Document…</option>{docs.map((d) => <option key={d}>{d}</option>)}</Select></div>
              <Input aria-label={`Citation ${i + 1} page`} className="w-20" inputMode="numeric" placeholder="Page" value={c.page || ""} onChange={(e) => cite(i, { page: Number(e.target.value.replace(/\D/g, "")) })} />
              <Button variant="ghost" size="icon" aria-label={`Remove citation ${i + 1}`} onClick={() => set("citations", f.citations.filter((_, j) => j !== i))}><Trash2 aria-hidden /></Button>
            </div>
          ))}
          <div><Button variant="outline" size="sm" onClick={() => set("citations", [...f.citations, { document: "", page: 0 }])}><Plus aria-hidden />Add citation</Button></div>
        </fieldset>
        {existing && existing.status !== "draft" && <p className="status-note" data-tone="warning">Saving changes returns this finding to draft so it is approved again.</p>}
        <div className="flex justify-end gap-2"><Button variant="ghost" onClick={onClose}>Cancel</Button><Button type="submit" disabled={busy || !f.title.trim()}>Save draft</Button></div>
        {blockers.length > 0 && <p className="text-xs text-muted">To approve: {blockers.join(" ")}</p>}
      </form>
    </Dialog>
  );
}

export function FindingsTab({ id }: { id: string }) {
  const { data, error, reload } = useAsync(async () => ({ findings: await listFindings(id), docs: (await listDocuments(id)).map((d) => d.name) }), [id]);
  const [editing, setEditing] = useState<Finding | "new" | null>(null);
  const [problem, setProblem] = useState("");
  async function move(f: Finding, status: Finding["status"]) {
    setProblem("");
    try { await setFindingStatus(f.id, status); reload(); } catch (e) { setProblem((e as Error).message); }
  }
  return (
    <>
      <PageHeader title="Findings" description="Drafts stay on your side. Only issued findings reach the client, who then submits a management response."
        actions={<Button onClick={() => setEditing("new")}><Plus aria-hidden />New finding</Button>} />
      <MockNotice />
      {problem && <p role="alert" className="status-note mb-4" data-tone="warning">{problem}</p>}
      {!data ? <Loading error={error} retry={reload} label="Loading findings…" /> : data.findings.length === 0 ? (
        <EmptyState icon={FileWarning} title="No findings" description="Record a finding when a test shows a gap against a rule." action={<Button onClick={() => setEditing("new")}>New finding</Button>} />
      ) : (
        <div className="grid gap-3">
          {data.findings.map((f) => (
            <Card key={f.id}>
              <CardHeader className="flex-row flex-wrap items-start justify-between gap-2">
                <div className="min-w-0"><CardTitle>{f.title}</CardTitle><p className="mt-1 text-xs text-muted">{f.rule}</p></div>
                <div className="flex gap-2"><SeverityBadge value={f.severity} /><FindingStatusBadge value={f.status} /></div>
              </CardHeader>
              <CardContent className="grid gap-3 text-sm">
                <dl className="grid gap-3 sm:grid-cols-2">
                  {([["Condition", f.condition], ["Cause", f.cause], ["Effect", f.effect], ["Recommendation", f.recommendation]] as const).map(([k, v]) => <div key={k}><dt className="text-muted">{k}</dt><dd>{v || "—"}</dd></div>)}
                </dl>
                <p className="text-xs text-muted">Cited: {f.citations.length ? f.citations.map((c) => `${c.document}, p.${c.page}`).join("; ") : "none yet"}</p>
                {(f.managementResponse || f.status === "issued") && (
                  <div className="rounded-lg bg-elevated p-3"><p className="text-xs font-medium text-muted">Management response {f.respondedAt ? `· ${fmtDate(f.respondedAt)}` : ""}</p><p className="mt-1">{f.managementResponse || "Awaiting the client’s response."}</p></div>
                )}
                <div className="flex flex-wrap gap-2 border-t border-border pt-3">
                  <Button size="sm" variant="outline" onClick={() => setEditing(f)}>Edit</Button>
                  {f.status === "draft" && <><Button size="sm" onClick={() => void move(f, "approved")}>Approve</Button><Button size="sm" variant="destructive" onClick={async () => { await deleteDraftFinding(f.id); reload(); }}>Delete draft</Button></>}
                  {f.status === "approved" && <><Button size="sm" onClick={() => void move(f, "issued")}>Issue to client</Button><Button size="sm" variant="ghost" onClick={() => void move(f, "draft")}>Return to draft</Button></>}
                  {(f.status === "responded" || f.status === "issued") && <Button size="sm" variant="secondary" onClick={() => void move(f, "closed")}>Close finding</Button>}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
      {editing && data && <FindingForm key={editing === "new" ? "new" : editing.id} id={id} existing={editing === "new" ? undefined : editing} docs={data.docs} onClose={() => setEditing(null)} onSaved={reload} />}
    </>
  );
}
