"use client";

import { useRef, useState } from "react";
import { Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useAsync } from "../kit";
import { acceptAiDraft, editAiDraft, getAiAnalysis, rejectAiDraft, runAiAnalysis, type AiDraft } from "@/lib/api/index";

const KIND_LABEL: Record<AiDraft["kind"], string> = { finding: "Possible finding", document_flag: "Document flag", client_request: "Suggested client request" };

function EditDialog({ draft, onClose, onSaved }: { draft: AiDraft; onClose: () => void; onSaved: () => void }) {
  const [title, setTitle] = useState(draft.title);
  const [body, setBody] = useState(draft.body);
  const [problem, setProblem] = useState("");
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()} title="Edit AI draft" description={`${draft.documentName}, page ${draft.page}. Your edit stays internal.`}>
      <form className="grid gap-3" onSubmit={async (e) => { e.preventDefault(); try { await editAiDraft(draft.id, title, body); onSaved(); onClose(); } catch (err) { setProblem((err as Error).message); } }}>
        <Field label="Title"><Input value={title} onChange={(e) => setTitle(e.target.value)} /></Field>
        <Field label="Text"><Textarea value={body} onChange={(e) => setBody(e.target.value)} /></Field>
        {problem && <p role="alert" className="status-note" data-tone="warning">{problem}</p>}
        <div className="flex justify-end gap-2"><Button variant="ghost" onClick={onClose}>Cancel</Button><Button type="submit" disabled={!title.trim() || !body.trim()}>Save edit</Button></div>
      </form>
    </Dialog>
  );
}

/**
 * Auditor-only panel. Renders nothing at all unless the server says AI analysis is switched on
 * (the routes answer 404 when it is off). Drafts are internal: Accept only copies a draft into an
 * ordinary draft finding, which still needs your approval and release before a client sees anything.
 */
export function AiAnalysisPanel({ engagementId, onAccepted }: { engagementId: string; onAccepted: () => void }) {
  const { data: loaded, error, reload, setData } = useAsync(async () => ({ value: await getAiAnalysis(engagementId) }), [engagementId]);
  const [busy, setBusy] = useState(false);
  const running = useRef(false); // blocks a second click before React re-renders the disabled button
  const [problem, setProblem] = useState("");
  const [editing, setEditing] = useState<AiDraft | null>(null);

  // Loading, switched off (server answers 404) or a load error: render nothing, never a button.
  if (!loaded || !loaded.value) return error ? <p role="alert" className="status-note mb-4" data-tone="warning">{error}</p> : null;
  const data = loaded.value;

  async function act(fn: () => Promise<unknown>, accepted = false) {
    setProblem("");
    try { await fn(); reload(); if (accepted) onAccepted(); } catch (e) { setProblem((e as Error).message); }
  }
  const pending = data.drafts.filter((d) => d.status === "pending");
  const decided = data.drafts.filter((d) => d.status !== "pending");
  return (
    <Card className="mb-6" data-testid="ai-analysis">
      <CardHeader className="flex-row flex-wrap items-start justify-between gap-2">
        <div>
          <CardTitle>AI analysis</CardTitle>
          <p className="mt-1 text-xs text-muted">Drafts only, for you alone. Nothing reaches the client unless you accept a draft and release it yourself. SAR material is never read.</p>
        </div>
        <Button size="sm" disabled={busy} onClick={async () => { if (running.current) return; running.current = true; setBusy(true); try { await act(() => runAiAnalysis(engagementId).then((next) => setData({ value: next }))); } finally { running.current = false; setBusy(false); } }}>
          <Sparkles aria-hidden />{busy ? "Analysing…" : "Run AI analysis"}
        </Button>
      </CardHeader>
      <CardContent className="grid gap-3 text-sm">
        {problem && <p role="alert" className="status-note" data-tone="warning">{problem}</p>}
        {data.lastRun && (
          <p className="text-xs text-muted">
            Last run: {data.lastRun.documentsAnalyzed} file{data.lastRun.documentsAnalyzed === 1 ? "" : "s"} analysed{data.lastRun.models.length ? ` with ${data.lastRun.models.join(", ")}` : ""}.
          </p>
        )}
        {data.lastRun && data.lastRun.skipped.length > 0 && (
          <div className="rounded-lg bg-elevated p-3" data-testid="ai-skipped">
            <p className="text-xs font-medium text-muted">Skipped, not read by the AI</p>
            <ul className="mt-1 grid gap-1">{data.lastRun.skipped.map((s) => <li key={s.documentId}><span className="font-medium">{s.document}</span>: {s.reason}</li>)}</ul>
          </div>
        )}
        {pending.length === 0 && <p className="text-muted">{data.lastRun ? "No drafts waiting for review." : "No analysis has been run yet."}</p>}
        {pending.map((d) => (
          <div key={d.id} className="grid gap-2 rounded-lg border border-border p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="font-medium">{d.title}</p>
              <Badge>{KIND_LABEL[d.kind]}</Badge>
            </div>
            <p>{d.body}</p>
            <p className="text-xs text-muted">Cited: {d.documentName}, p.{d.page} · {d.itemKey} · AI draft{d.edited ? ", edited by you" : ""}</p>
            <div className="flex flex-wrap gap-2">
              <Button size="sm" onClick={() => void act(() => acceptAiDraft(d.id), true)}>Accept</Button>
              <Button size="sm" variant="outline" onClick={() => setEditing(d)}>Edit</Button>
              <Button size="sm" variant="ghost" onClick={() => void act(() => rejectAiDraft(d.id))}>Reject</Button>
            </div>
          </div>
        ))}
        {decided.length > 0 && <p className="text-xs text-muted">{decided.filter((d) => d.status === "accepted").length} accepted as draft findings, {decided.filter((d) => d.status === "rejected").length} rejected.</p>}
      </CardContent>
      {editing && <EditDialog key={editing.id} draft={editing} onClose={() => setEditing(null)} onSaved={reload} />}
    </Card>
  );
}
