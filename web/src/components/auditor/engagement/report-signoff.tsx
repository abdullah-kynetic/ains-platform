"use client";

import { useState } from "react";
import { Check, Download, Fingerprint, Printer } from "lucide-react";
import { PageHeader } from "@/components/shell/page";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { approveAsReviewer, buildReport, completeEngagement, downloadWord, getEngagementSummary, getIndependence, getSignoff, partnerSign, reportFingerprint, saveIndependence, saveReportSection, signoffBlockers, type IndependenceRecord, type ReportSection } from "@/lib/api/index";
import { Loading, MockNotice, fmtDateTime, useAsync } from "../kit";

export function ReportTab({ id }: { id: string }) {
  const { data, error, reload } = useAsync(async () => {
    const [draft, signoff, summary] = await Promise.all([buildReport(id), getSignoff(id), getEngagementSummary(id)]);
    return { draft, signoff, summary, fingerprint: await reportFingerprint(draft.sections) };
  }, [id]);
  const [editing, setEditing] = useState<string | null>(null);
  const [text, setText] = useState("");
  if (!data) return <Loading error={error} retry={reload} label="Assembling report…" />;
  const { draft, signoff, summary, fingerprint } = data;
  const signed = !!signoff.partner.signedAt;
  const title = `${summary?.firmName ?? "Engagement"} AML independent test ${summary?.period ?? ""}`.trim();
  return (
    <>
      <PageHeader title="Report" description="Sections are assembled from your tested results and approved findings. Draft findings are left out."
        actions={<><Button variant="outline" onClick={() => downloadWord(title, draft.sections, signed ? signoff.partner.fingerprint : null)}><Download aria-hidden />Word</Button><Button variant="outline" onClick={() => window.print()}><Printer aria-hidden />PDF</Button></>} />
      <MockNotice>Synthetic preview data. Word and PDF are browser-generated previews; the server will render the signed template.</MockNotice>
      <div className="mb-4 flex flex-wrap items-center gap-3 rounded-xl border border-border bg-surface px-4 py-3 text-sm">
        <Fingerprint aria-hidden className="size-4 text-muted" />
        <span className="text-muted">Report fingerprint (SHA-256)</span><code className="break-all text-xs" data-testid="fingerprint">{fingerprint}</code>
        {signed ? (signoff.partner.fingerprint === fingerprint ? <Badge variant="success">Matches signed copy</Badge> : <Badge variant="danger">Changed since signing</Badge>) : <Badge>Draft, unsigned</Badge>}
      </div>
      <div className="report-print-area grid gap-3">
        <h2 className="hidden text-xl font-semibold print:block">{title}</h2>
        {draft.sections.map((s: ReportSection) => (
          <Card key={s.id}>
            <CardHeader className="flex-row items-center justify-between"><CardTitle>{s.title}</CardTitle>{!signed && editing !== s.id && <Button size="sm" variant="ghost" className="print:hidden" onClick={() => { setEditing(s.id); setText(s.body); }}>Edit</Button>}</CardHeader>
            <CardContent>
              {editing === s.id ? (
                <div className="grid gap-2"><Textarea aria-label={`Edit ${s.title}`} className="min-h-40" value={text} onChange={(e) => setText(e.target.value)} /><div className="flex gap-2"><Button size="sm" onClick={async () => { await saveReportSection(id, s.id, text); setEditing(null); reload(); }}>Save section</Button><Button size="sm" variant="ghost" onClick={() => setEditing(null)}>Cancel</Button></div></div>
              ) : s.body.split("\n").map((l, i) => <p key={i} className="text-sm leading-relaxed">{l}</p>)}
            </CardContent>
          </Card>
        ))}
        {signed && <p className="hidden text-xs print:block">Signed by {signoff.partner.name} on {fmtDateTime(signoff.partner.signedAt)}. Fingerprint {signoff.partner.fingerprint}</p>}
      </div>
    </>
  );
}

export function IndependenceTab({ id }: { id: string }) {
  const { data, error, reload } = useAsync(() => getIndependence(id), [id]);
  if (!data) return <Loading error={error} retry={reload} label="Loading independence record…" />;
  return <IndependenceForm key={data.declaredAt ?? "new"} id={id} data={data} onSaved={reload} />;
}

function IndependenceForm({ id, data, onSaved }: { id: string; data: IndependenceRecord; onSaved: () => void }) {
  const [answers, setAnswers] = useState<Record<string, "yes" | "no" | null>>(() => Object.fromEntries(data.answers.map((a) => [a.id, a.answer])));
  const [conflicts, setConflicts] = useState(data.conflicts);
  const [safeguards, setSafeguards] = useState(data.safeguards);
  const [saved, setSaved] = useState("");
  const anyYes = Object.values(answers).includes("yes");
  const complete = data.answers.every((a) => answers[a.id]);
  const label = { independent: "Independent", safeguards_required: "Independent with safeguards", not_independent: "Not independent" } as const;
  return (
    <>
      <PageHeader title="Independence" description="Declared before testing starts. A “yes” needs a described conflict and the safeguards applied." badge={data.conclusion ? <Badge variant={data.conclusion === "not_independent" ? "danger" : "success"}>{label[data.conclusion]}</Badge> : <Badge>Not declared</Badge>} />
      <MockNotice />
      <form className="grid max-w-3xl gap-4" onSubmit={async (e) => { e.preventDefault(); const r = await saveIndependence(id, { answers: data.answers.map((a) => ({ ...a, answer: answers[a.id] ?? null })), conflicts, safeguards }); setSaved(r.conclusion ? `Recorded: ${label[r.conclusion]}.` : "Saved as incomplete."); onSaved(); }}>
        <Card>
          <CardContent className="grid gap-4">
            {data.answers.map((a) => (
              <fieldset key={a.id} className="grid gap-2 border-b border-border pb-4 last:border-0 last:pb-0">
                <legend className="mb-1 text-sm">{a.question}</legend>
                <div className="flex gap-4 text-sm">{(["no", "yes"] as const).map((v) => <label key={v} className="flex items-center gap-2"><input type="radio" className="size-4 accent-foreground" name={a.id} checked={answers[a.id] === v} onChange={() => setAnswers({ ...answers, [a.id]: v })} />{v === "yes" ? "Yes" : "No"}</label>)}</div>
              </fieldset>
            ))}
          </CardContent>
        </Card>
        {anyYes && (
          <Card><CardContent className="grid gap-3">
            <Field label="Describe the conflict"><Textarea value={conflicts} onChange={(e) => setConflicts(e.target.value)} /></Field>
            <Field label="Safeguards applied" hint="Leave empty and the engagement is recorded as not independent."><Textarea value={safeguards} onChange={(e) => setSafeguards(e.target.value)} /></Field>
          </CardContent></Card>
        )}
        <div className="flex flex-wrap items-center gap-3"><Button type="submit" disabled={!complete}>Declare independence</Button>{!complete && <span className="text-xs text-muted">Answer every question first.</span>}{saved && <span role="status" className="text-sm text-muted">{saved}</span>}</div>
        {data.declaredAt && <p className="text-xs text-muted">Last declared by {data.declaredBy} on {fmtDateTime(data.declaredAt)}.</p>}
      </form>
    </>
  );
}

export function SignoffTab({ id }: { id: string }) {
  const { data, error, reload } = useAsync(async () => {
    const [signoff, blockers, summary, draft] = await Promise.all([getSignoff(id), signoffBlockers(id), getEngagementSummary(id), buildReport(id)]);
    return { signoff, blockers, summary, fingerprint: await reportFingerprint(draft.sections) };
  }, [id]);
  const [note, setNote] = useState("");
  const [typed, setTyped] = useState("");
  const [attest, setAttest] = useState(false);
  const [problem, setProblem] = useState("");
  if (!data) return <Loading error={error} retry={reload} label="Loading sign-off…" />;
  const { signoff, blockers, summary, fingerprint } = data;
  const run = async (fn: () => Promise<unknown>) => { setProblem(""); try { await fn(); reload(); } catch (e) { setProblem((e as Error).message); } };
  const step = (n: number, title: string, done: boolean, body: React.ReactNode) => (
    <Card><CardHeader className="flex-row items-center gap-3"><span aria-hidden className={`grid size-6 place-items-center rounded-full border text-xs ${done ? "border-success bg-success/10 text-success-foreground" : "border-border-strong text-muted"}`}>{done ? <Check className="size-3.5" /> : n}</span><CardTitle>{title}</CardTitle>{done && <Badge variant="success" className="ml-auto">Done</Badge>}</CardHeader><CardContent>{body}</CardContent></Card>
  );
  return (
    <>
      <PageHeader title="Sign-off" description="Second reviewer approves, then the partner signs the exact report fingerprint. Nothing is signed automatically."
        badge={signoff.completedAt ? <Badge variant="success">Complete</Badge> : <Badge variant="brand">In review</Badge>} />
      <MockNotice />
      {problem && <p role="alert" className="status-note mb-4" data-tone="warning">{problem}</p>}
      <div className="grid max-w-3xl gap-3">
        {step(1, "Readiness", blockers.length === 0, blockers.length === 0 ? <p className="text-sm text-muted">Checklist, samples, workpapers, findings and independence are all complete.</p> : <ul className="grid gap-2 text-sm">{blockers.map((b) => <li key={b} className="flex gap-2"><span aria-hidden className="mt-2 size-1.5 shrink-0 rounded-full bg-warning" />{b}</li>)}</ul>)}
        {step(2, `Second reviewer: ${signoff.reviewer.name}`, !!signoff.reviewer.approvedAt, signoff.reviewer.approvedAt ? <p className="text-sm text-muted">Approved {fmtDateTime(signoff.reviewer.approvedAt)}. {signoff.reviewer.note}</p> : (
          <div className="grid gap-3"><Field label="Review note (optional)"><Textarea value={note} onChange={(e) => setNote(e.target.value)} /></Field><div><Button disabled={blockers.length > 0} onClick={() => void run(() => approveAsReviewer(id, note))}>Approve as second reviewer</Button></div></div>
        ))}
        {step(3, `Partner sign-off: ${signoff.partner.name}`, !!signoff.partner.signedAt, signoff.partner.signedAt ? (
          <div className="grid gap-1 text-sm"><p className="text-muted">Signed {fmtDateTime(signoff.partner.signedAt)}</p><p className="break-all"><span className="text-muted">Fingerprint </span><code className="text-xs">{signoff.partner.fingerprint}</code></p>{signoff.partner.fingerprint !== fingerprint && <p className="status-note" data-tone="danger">The report has changed since it was signed.</p>}</div>
        ) : (
          <div className="grid gap-3">
            <p className="text-sm"><span className="text-muted">Report fingerprint to be signed </span><code className="break-all text-xs">{fingerprint}</code></p>
            <label className="flex items-start gap-2 text-sm"><input type="checkbox" className="mt-0.5 size-4 accent-foreground" checked={attest} onChange={(e) => setAttest(e.target.checked)} />I have reviewed this report and approve the findings in it.</label>
            <Field label={signoff.partner.name ? `Type “${signoff.partner.name}” to sign` : "Type your full name to sign"}><Input value={typed} onChange={(e) => setTyped(e.target.value)} autoComplete="off" /></Field>
            <div><Button disabled={!signoff.reviewer.approvedAt || !attest || !typed.trim()} onClick={() => void run(() => partnerSign(id, typed))}>Sign report</Button>{!signoff.reviewer.approvedAt && <span className="ml-3 text-xs text-muted">Needs the second reviewer first.</span>}</div>
          </div>
        ))}
        {step(4, "Mark engagement complete", !!signoff.completedAt, signoff.completedAt ? <p className="text-sm text-muted">Completed {fmtDateTime(signoff.completedAt)} for {summary?.firmName}.</p> : <div><Button variant="outline" disabled={!signoff.partner.signedAt} onClick={() => void run(() => completeEngagement(id))}>Mark complete</Button></div>)}
      </div>
    </>
  );
}
