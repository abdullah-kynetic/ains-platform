"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { AuthGate } from "@/components/auth/session";
import { PageHeader } from "@/components/shell/page";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  createDraftEngagement, getChecklistReview, listManagedEngagements,
  publishChecklist, releaseFollowUp, type ChecklistReview, type ManagedEngagement,
} from "@/lib/api";

function EngagementManager() {
  const [engagements, setEngagements] = useState<ManagedEngagement[]>([]);
  const [review, setReview] = useState<ChecklistReview | null>(null);
  const [notes, setNotes] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [selection, setSelection] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    listManagedEngagements().then(setEngagements).catch((caught: unknown) => {
      setError(caught instanceof Error ? caught.message : "Could not load engagements.");
    });
  }, []);

  async function act(action: () => Promise<void>) {
    setBusy(true);
    setError("");
    try { await action(); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Could not save."); }
    finally { setBusy(false); }
  }

  function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    void act(async () => {
      const created = await createDraftEngagement({
        firmName: String(values.get("firmName")), firmSlug: String(values.get("firmSlug")),
        reviewPeriodStart: String(values.get("start")), reviewPeriodEnd: String(values.get("end")),
        dueDate: String(values.get("due")) || null,
      });
      setEngagements((current) => [...current, created]);
      setReview(await getChecklistReview(created.id));
      setConfirmed(false);
      setNotes("");
      form.reset();
    });
  }

  return <>
    <PageHeader title="Engagement setup" description="Create a firm, review its request list, and publish it when ready for client intake." />
    {error ? <p className="mb-4 text-sm text-red-400" role="alert">{error}</p> : null}
    <Card className="mb-5">
      <CardHeader><CardTitle>New firm and engagement</CardTitle></CardHeader>
      <CardContent>
        <form onSubmit={create} className="grid gap-4 sm:grid-cols-2">
          <Field label="Firm name" htmlFor="firm-name"><Input id="firm-name" name="firmName" required maxLength={255} /></Field>
          <Field label="Firm identifier" htmlFor="firm-slug" hint="Unique lowercase letters, numbers, and hyphens; at least 3 characters."><Input id="firm-slug" name="firmSlug" required pattern="[a-z0-9][a-z0-9-]{1,98}[a-z0-9]" /></Field>
          <Field label="Review period start" htmlFor="period-start"><Input id="period-start" name="start" type="date" required /></Field>
          <Field label="Review period end" htmlFor="period-end"><Input id="period-end" name="end" type="date" required /></Field>
          <Field label="Document deadline" htmlFor="deadline"><Input id="deadline" name="due" type="date" /></Field>
          <Button type="submit" disabled={busy} className="self-end">Create draft</Button>
        </form>
      </CardContent>
    </Card>
    <div className="mb-5 grid gap-2">
      {engagements.map((engagement) => <Card key={engagement.id}>
        <CardContent className="flex flex-wrap items-center justify-between gap-3 pt-5">
          <div><p>{engagement.firmName}</p><p className="text-xs text-muted">{engagement.status} · {engagement.itemCount} requests</p></div>
          <div className="flex gap-2">
            {engagement.checklistVersion ? <Button variant="outline" disabled={busy} onClick={() => void act(async () => {
              setReview(await getChecklistReview(engagement.id)); setConfirmed(false); setNotes("");
            })}>Review requests</Button> : null}
            <Link className={buttonVariants({ variant: "outline" })} href={`/auditor/engagements/${engagement.id}`}>Evidence queue</Link>
          </div>
        </CardContent>
      </Card>)}
    </div>
    {review ? <Card>
      <CardHeader><CardTitle>{review.engagement.firmName} — checklist review</CardTitle></CardHeader>
      <CardContent className="grid gap-4">
        <p className="text-sm text-muted">Confirm source numbering, the request 9 cross-reference, period requirements, written representations, and restricted handling before publishing.</p>
        {review.catalog.items.map((item) => <details key={item.id} className="rounded-lg border border-border p-3">
          <summary className="cursor-pointer text-sm font-medium">{item.id}: {item.title}{item.restricted ? " — do not upload" : ""}</summary>
          <p className="mt-2 text-sm text-muted">{item.description}</p>
          <p className="mt-2 text-sm text-muted">Timing: {item.review_period_rule}</p>
          {item.condition_question ? <p className="mt-2 text-sm">{item.condition_question}</p> : null}
          {item.negative_answer_instruction ? <p className="mt-2 text-sm">If no: {item.negative_answer_instruction}</p> : null}
        </details>)}
        {review.engagement.status === "draft" ? <>
          <Field label="Checklist review notes"><Textarea value={notes} onChange={(event) => setNotes(event.target.value)} minLength={10} maxLength={5000} /></Field>
          <label className="flex gap-2 text-sm"><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />I reviewed this engagement’s checklist and approve it for client intake.</label>
          <Button disabled={busy || !confirmed || notes.trim().length < 10} onClick={() => void act(async () => {
            await publishChecklist(review.engagement.id, notes);
            setReview(await getChecklistReview(review.engagement.id));
            setEngagements(await listManagedEngagements());
          })}>Approve and publish requests</Button>
        </> : review.engagement.status === "collecting" ? <>
          <Field label="Accounts or engagements selected for follow-up" hint="Record the selection and coordinate it with the client."><Textarea value={selection} onChange={(event) => setSelection(event.target.value)} maxLength={5000} /></Field>
          {review.followUps.map((item) => <Button key={item.id} disabled={busy || item.released || selection.trim().length < 10} onClick={() => void act(async () => {
            await releaseFollowUp(review.engagement.id, item.id, selection);
            setReview(await getChecklistReview(review.engagement.id));
          })}>{item.released ? "Released" : "Release"}: {item.title}</Button>)}
        </> : null}
      </CardContent>
    </Card> : null}
  </>;
}

export default function EngagementSetupPage() {
  return <AuthGate role="auditor"><EngagementManager /></AuthGate>;
}
