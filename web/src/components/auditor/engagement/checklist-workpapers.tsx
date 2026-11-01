"use client";

import { useState } from "react";
import { ClipboardList } from "lucide-react";
import { PageHeader } from "@/components/shell/page";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { getChecklistTests, listDocuments, listWorkpapers, reviewWorkpaper, saveWorkpaper, setConclusion, type ChecklistTest, type Conclusion, type Workpaper } from "@/lib/api/index";
import { sectionName } from "@/lib/mock/seed";
import { ConclusionBadge, Loading, MockNotice, conclusionMeta, fmtDate, useAsync } from "../kit";

const options: Conclusion[] = ["pass", "partial", "fail", "na"];

export function ChecklistTab({ id }: { id: string }) {
  const { data, error, reload, setData } = useAsync(() => getChecklistTests(id), [id]);
  const [filter, setFilter] = useState("all");
  const [announce, setAnnounce] = useState("");
  async function change(row: ChecklistTest, value: string) {
    const next = await setConclusion(id, row.requestId, (value || null) as Conclusion | null);
    setData(next);
    setAnnounce(`${row.requestId} set to ${value ? conclusionMeta[value as Conclusion].label : "not tested"}.`);
  }
  if (!data) return <Loading error={error} retry={reload} label="Loading checklist…" />;
  const count = (c: Conclusion | "open") => data.filter((t) => (c === "open" ? t.conclusion === null : t.conclusion === c)).length;
  const rows = data.filter((t) => filter === "all" || (filter === "open" ? t.conclusion === null : t.conclusion === filter));
  return (
    <>
      <PageHeader title="Checklist" description={`All ${data.length} requests. Record the test conclusion for each. Items marked does not apply sort to the bottom and still count as resolved.`} />
      <MockNotice />
      <div className="mb-4 flex flex-wrap items-center gap-2" role="group" aria-label="Filter by conclusion">
        {([["all", `All ${data.length}`], ["open", `Not tested ${count("open")}`], ...options.map((o) => [o, `${conclusionMeta[o].label} ${count(o)}`])] as [string, string][]).map(([v, label]) => (
          <Button key={v} size="sm" variant={filter === v ? "default" : "outline"} aria-pressed={filter === v} onClick={() => setFilter(v)}>{label}</Button>
        ))}
      </div>
      <p role="status" className="sr-only">{announce}</p>
      {rows.length === 0 ? <EmptyState icon={ClipboardList} title="Nothing in this view" description="Choose another filter." /> : (
        <Table>
          <THead><TR><TH>ID</TH><TH>Request</TH><TH>Section</TH><TH>Conclusion</TH></TR></THead>
          <TBody>
            {rows.map((t) => (
              <TR key={t.requestId} className={t.conclusion === "na" ? "text-muted" : undefined}>
                <TD className="whitespace-nowrap font-mono text-xs">{t.requestId}</TD>
                <TD className="font-medium">{t.title}{t.restricted && <Badge className="ml-2" variant="danger">Auditor-handled</Badge>}</TD>
                <TD className="text-muted">{sectionName(t.section)}</TD>
                <TD className="w-52">
                  <Select aria-label={`Conclusion for ${t.requestId} ${t.title}`} value={t.conclusion ?? ""} onChange={(e) => void change(t, e.target.value)}>
                    <option value="">Not tested</option>
                    {options.map((o) => <option key={o} value={o}>{conclusionMeta[o].label}</option>)}
                  </Select>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}
    </>
  );
}

export function WorkpapersTab({ id }: { id: string }) {
  const { data, error, reload, setData } = useAsync(async () => {
    const [tests, papers, docs] = await Promise.all([getChecklistTests(id), listWorkpapers(id), listDocuments(id)]);
    return { tests, papers, docs };
  }, [id]);
  const [openId, setOpenId] = useState<string | null>(null);
  if (!data) return <Loading error={error} retry={reload} label="Loading workpapers…" />;
  const paper = (rid: string) => data.papers.find((p) => p.requestId === rid);
  const test = data.tests.find((t) => t.requestId === openId);
  const state = (p?: Workpaper) => (!p ? <Badge>No workpaper</Badge> : p.reviewedAt ? <Badge variant="success">Reviewed</Badge> : <Badge variant="warning">Needs review</Badge>);
  return (
    <>
      <PageHeader title="Workpapers" description="For each request: the procedure performed, the evidence relied on, the conclusion, and who prepared and reviewed it." />
      <MockNotice />
      <Table>
        <THead><TR><TH>Request</TH><TH>Conclusion</TH><TH>Preparer</TH><TH>Reviewer</TH><TH>Status</TH><TH><span className="sr-only">Open</span></TH></TR></THead>
        <TBody>
          {data.tests.filter((t) => t.conclusion !== "na").map((t) => {
            const p = paper(t.requestId);
            return (
              <TR key={t.requestId}>
                <TD><span className="font-mono text-xs text-muted">{t.requestId}</span><div className="font-medium">{t.title}</div></TD>
                <TD><ConclusionBadge value={p?.conclusion ?? t.conclusion} /></TD>
                <TD>{p?.preparer || "—"}<div className="text-xs text-muted">{fmtDate(p?.preparedAt ?? null)}</div></TD>
                <TD>{p?.reviewer || "—"}<div className="text-xs text-muted">{fmtDate(p?.reviewedAt ?? null)}</div></TD>
                <TD>{state(p)}</TD>
                <TD className="text-right"><Button size="sm" variant="outline" onClick={() => setOpenId(t.requestId)}>{p ? "Open" : "Start"}<span className="sr-only"> workpaper for {t.requestId}</span></Button></TD>
              </TR>
            );
          })}
        </TBody>
      </Table>
      {test && (
        <WorkpaperDialog key={test.requestId} engagementId={id} test={test} paper={paper(test.requestId)} docs={data.docs.filter((d) => d.engagementId === id)}
          onClose={() => setOpenId(null)} onSaved={(papers) => setData({ ...data, papers })} />
      )}
    </>
  );
}

function WorkpaperDialog({ engagementId, test, paper, docs, onClose, onSaved }: { engagementId: string; test: ChecklistTest; paper?: Workpaper; docs: { id: string; name: string; requestId: string }[]; onClose: () => void; onSaved: (p: Workpaper[]) => void }) {
  const [procedure, setProcedure] = useState(paper?.procedure ?? "");
  const [evidence, setEvidence] = useState<string[]>(paper?.evidenceIds ?? []);
  const [conclusion, setConclusion] = useState<Conclusion | "">(paper?.conclusion ?? "");
  const [busy, setBusy] = useState(false);
  const valid = procedure.trim().length > 10 && conclusion && (evidence.length > 0 || conclusion === "na");
  async function save() {
    setBusy(true);
    await saveWorkpaper(engagementId, { requestId: test.requestId, procedure, evidenceIds: evidence, conclusion: conclusion || null });
    onSaved(await listWorkpapers(engagementId));
    setBusy(false); onClose();
  }
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()} className="max-w-2xl" title={`Workpaper: ${test.requestId}`} description={test.title}>
      <div className="grid gap-4">
        <Field label="Procedure performed" hint="What you did, in enough detail for a reviewer to repeat it."><Textarea value={procedure} onChange={(e) => setProcedure(e.target.value)} /></Field>
        <fieldset className="grid gap-2">
          <legend className="mb-1 text-sm font-medium">Evidence relied on</legend>
          {docs.length === 0 ? <p className="text-sm text-muted">No documents uploaded for this engagement yet.</p> : docs.map((d) => (
            <label key={d.id} className="flex items-center gap-2 text-sm"><input type="checkbox" className="size-4 accent-foreground" checked={evidence.includes(d.id)} onChange={(e) => setEvidence(e.target.checked ? [...evidence, d.id] : evidence.filter((x) => x !== d.id))} />{d.name}<span className="text-xs text-muted">{d.requestId}</span></label>
          ))}
        </fieldset>
        <Field label="Conclusion"><Select value={conclusion} onChange={(e) => setConclusion(e.target.value as Conclusion)}><option value="">Choose…</option>{options.map((o) => <option key={o} value={o}>{conclusionMeta[o].label}</option>)}</Select></Field>
        <div className="grid gap-1 rounded-lg bg-elevated p-3 text-sm sm:grid-cols-2">
          <p><span className="text-muted">Preparer </span>{paper?.preparer || "You, on save"}</p>
          <p><span className="text-muted">Reviewer </span>{paper?.reviewer || "Not yet reviewed"}</p>
        </div>
        <p className="text-xs text-muted">Saving a changed procedure or conclusion clears any earlier review.</p>
        <div className="flex flex-wrap justify-between gap-2">
          <Button variant="outline" disabled={!paper || !!paper.reviewedAt || busy} onClick={async () => { onSaved(await reviewWorkpaper(engagementId, test.requestId)); onClose(); }}>Mark reviewed (second reviewer)</Button>
          <div className="flex gap-2"><Button variant="ghost" onClick={onClose}>Cancel</Button><Button disabled={!valid || busy} onClick={() => void save()}>Save workpaper</Button></div>
        </div>
      </div>
    </Dialog>
  );
}
