"use client";

import { useState } from "react";
import { Plus, Shuffle } from "lucide-react";
import { PageHeader } from "@/components/shell/page";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { createSample, listSamples, sampleStats, setSampleResult, type SampleResult, type SampleSet } from "@/lib/api/index";
import { Loading, MockNotice, useAsync } from "../kit";

function NewSample({ id, onCreated }: { id: string; onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ area: "", population: "", sampleSize: "", method: "Random" });
  const pop = Number(f.population), size = Number(f.sampleSize);
  const problem = !f.area.trim() ? "Name the area being tested." : !(pop > 0) ? "Enter the population size." : !(size > 0) ? "Enter the sample size." : size > pop ? "The sample cannot be larger than the population." : size > 100 ? "Samples above 100 items need partner approval." : "";
  return (
    <>
      <Button onClick={() => setOpen(true)}><Plus aria-hidden />New sample</Button>
      <Dialog open={open} onOpenChange={setOpen} title="New sample" description="Record the population and how many items you will test.">
        <form className="grid gap-3" onSubmit={async (e) => { e.preventDefault(); if (problem) return; await createSample(id, { area: f.area, requestId: null, population: pop, sampleSize: size, method: f.method }); setOpen(false); setF({ area: "", population: "", sampleSize: "", method: "Random" }); onCreated(); }}>
          <Field label="Area tested"><Input value={f.area} onChange={(e) => setF({ ...f, area: e.target.value })} /></Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Population"><Input inputMode="numeric" value={f.population} onChange={(e) => setF({ ...f, population: e.target.value.replace(/\D/g, "") })} /></Field>
            <Field label="Sample size"><Input inputMode="numeric" value={f.sampleSize} onChange={(e) => setF({ ...f, sampleSize: e.target.value.replace(/\D/g, "") })} /></Field>
          </div>
          <Field label="Selection method"><Select value={f.method} onChange={(e) => setF({ ...f, method: e.target.value })}><option>Random</option><option>Random, seeded</option><option>Stratified by account type</option><option>Judgmental (document why)</option></Select></Field>
          {problem && <p className="status-note" data-tone="warning">{problem}</p>}
          <div className="flex justify-end gap-2"><Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" disabled={!!problem}>Create sample</Button></div>
        </form>
      </Dialog>
    </>
  );
}

function SetCard({ set, onChange }: { set: SampleSet; onChange: (rows: SampleSet[]) => void }) {
  const s = sampleStats(set);
  return (
    <details className="group rounded-xl border border-border bg-surface" open={set.items.length <= 25}>
      <summary className="flex cursor-pointer flex-wrap items-center justify-between gap-3 px-4 py-3">
        <div><p className="text-sm font-medium">{set.area}</p><p className="text-xs text-muted">Population {set.population} · sample {set.sampleSize} · {set.method}</p></div>
        <div className="flex gap-2"><Badge>{s.tested} of {set.sampleSize} tested</Badge>{s.exceptions > 0 ? <Badge variant="danger">{s.exceptions} exception{s.exceptions > 1 ? "s" : ""}</Badge> : s.tested === set.sampleSize ? <Badge variant="success">No exceptions</Badge> : null}</div>
      </summary>
      <div className="border-t border-border">
        <Table bare>
          <THead><TR><TH>Item</TH><TH>Result</TH><TH>Note (required for exceptions)</TH></TR></THead>
          <TBody>
            {set.items.map((i) => (
              <TR key={i.id}>
                <TD className="font-mono text-xs">{i.reference}</TD>
                <TD className="w-44"><Select aria-label={`Result for ${i.reference}`} value={i.result} onChange={async (e) => onChange(await setSampleResult(set.id, i.id, e.target.value as SampleResult))}><option value="pending">Untested</option><option value="pass">Pass</option><option value="exception">Exception</option></Select></TD>
                <TD><Input aria-label={`Note for ${i.reference}`} aria-invalid={i.result === "exception" && !i.note.trim()} defaultValue={i.note} placeholder={i.result === "exception" ? "Describe the exception" : ""} onBlur={async (e) => { if (e.target.value !== i.note) onChange(await setSampleResult(set.id, i.id, i.result, e.target.value)); }} /></TD>
              </TR>
            ))}
          </TBody>
        </Table>
      </div>
    </details>
  );
}

export function SamplesTab({ id }: { id: string }) {
  const { data, error, reload, setData } = useAsync(() => listSamples(id), [id]);
  return (
    <>
      <PageHeader title="Samples" description="Population, sample size, selected items and the result of each test. Exceptions feed the findings." actions={<NewSample id={id} onCreated={reload} />} />
      <MockNotice />
      {!data ? <Loading error={error} retry={reload} label="Loading samples…" /> : data.length === 0 ? (
        <EmptyState icon={Shuffle} title="No samples yet" description="Create a sample when a request needs item-level testing." />
      ) : <div className="grid gap-3">{data.map((s) => <SetCard key={s.id} set={s} onChange={setData} />)}</div>}
    </>
  );
}
