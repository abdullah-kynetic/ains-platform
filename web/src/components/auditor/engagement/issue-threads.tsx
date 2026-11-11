"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { flagIssue, ISSUE_LABEL, replyIssue, resolveIssue, type Issue, type IssueKind, type ProgressItem } from "@/lib/api/flow";

const KINDS = Object.keys(ISSUE_LABEL) as IssueKind[];

/** Quentin flags a document problem on a submitted request. The client sees only this note. */
export function FlagForm({ engagementId, item, onDone }: { engagementId: string; item: ProgressItem; onDone: () => void }) {
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState<IssueKind>("incorrect");
  const [documentId, setDocumentId] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  if (!open) {
    return (
      <Button size="sm" variant="outline" aria-label={`Flag ${item.requestId}`} onClick={() => setOpen(true)}>
        Flag a problem
      </Button>
    );
  }
  return (
    <form
      className="grid w-full gap-2 rounded-lg border border-border p-3"
      onSubmit={(event) => {
        event.preventDefault();
        setBusy(true);
        setError("");
        flagIssue(engagementId, item.id, { kind, note: note.trim(), ...(documentId ? { documentId } : {}) })
          .then(() => { setOpen(false); setNote(""); onDone(); })
          .catch((e: Error) => setError(e.message))
          .finally(() => setBusy(false));
      }}
    >
      <label className="grid gap-1 text-sm font-medium" htmlFor={`kind-${item.id}`}>
        Problem type
        <select id={`kind-${item.id}`} className="h-8 rounded-md border border-border bg-surface px-2 text-sm" value={kind} onChange={(e) => setKind(e.target.value as IssueKind)}>
          {KINDS.map((k) => <option key={k} value={k}>{ISSUE_LABEL[k]}</option>)}
        </select>
      </label>
      {item.documents.length ? (
        <label className="grid gap-1 text-sm font-medium" htmlFor={`doc-${item.id}`}>
          Which document
          <select id={`doc-${item.id}`} className="h-8 rounded-md border border-border bg-surface px-2 text-sm" value={documentId} onChange={(e) => setDocumentId(e.target.value)}>
            <option value="">Whole request</option>
            {item.documents.map((d) => <option key={d.id} value={d.id}>{d.number} · {d.name}</option>)}
          </select>
        </label>
      ) : null}
      <label className="grid gap-1 text-sm font-medium" htmlFor={`note-${item.id}`}>
        Note to the client (document issues only, never findings)
        <Textarea id={`note-${item.id}`} value={note} onChange={(e) => setNote(e.target.value)} maxLength={1000} required className="min-h-16" />
      </label>
      <div className="flex gap-2">
        <Button type="submit" size="sm" disabled={busy || !note.trim()}>{busy ? "Sending…" : "Send to client"}</Button>
        <Button type="button" size="sm" variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
      </div>
      {error ? <p role="alert" className="text-sm text-warning-foreground">{error}</p> : null}
    </form>
  );
}

/** One issue thread, used by the auditor tab and the client Messages page. */
export function IssueThread({ engagementId, issue, role, label, onDone }: { engagementId: string; issue: Issue; role: "auditor" | "client"; label: string; onDone: () => void }) {
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const run = (action: () => Promise<unknown>) => {
    setBusy(true);
    setError("");
    action().then(() => { setBody(""); onDone(); }).catch((e: Error) => setError(e.message)).finally(() => setBusy(false));
  };
  return (
    <article className="grid gap-2 rounded-xl border border-border bg-card p-4 shadow-card" data-testid={`issue-${issue.id}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-medium">{label}{issue.document?.number ? ` · document ${issue.document.number}` : ""}</p>
        <div className="flex gap-2">
          <Badge variant="warning">{ISSUE_LABEL[issue.kind]}</Badge>
          <Badge variant={issue.status === "open" ? "info" : "success"}>{issue.status === "open" ? "Open" : "Resolved"}</Badge>
        </div>
      </div>
      <ul className="grid gap-2 text-sm">
        {issue.messages.map((m) => (
          <li key={m.id} className="rounded-md bg-elevated p-2">
            <span className="text-xs text-muted">{m.authorRole === "auditor" ? "Your auditor" : "Client"}{m.documentNumber ? ` · attached ${m.documentNumber}` : ""}</span>
            <p>{m.body}</p>
          </li>
        ))}
      </ul>
      {issue.status === "open" ? (
        <div className="grid gap-2">
          <label className="grid gap-1 text-sm font-medium" htmlFor={`reply-${issue.id}`}>
            Reply
            <Textarea id={`reply-${issue.id}`} value={body} onChange={(e) => setBody(e.target.value)} maxLength={2000} className="min-h-16" />
          </label>
          <div className="flex gap-2">
            <Button size="sm" disabled={busy || !body.trim()} onClick={() => run(() => replyIssue(engagementId, issue.id, role, body.trim()))}>Send reply</Button>
            {role === "auditor" ? <Button size="sm" variant="outline" disabled={busy} onClick={() => run(() => resolveIssue(engagementId, issue.id))}>Mark resolved</Button> : null}
          </div>
        </div>
      ) : null}
      {error ? <p role="alert" className="text-sm text-warning-foreground">{error}</p> : null}
    </article>
  );
}
