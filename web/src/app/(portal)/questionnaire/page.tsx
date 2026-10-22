"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/shell/page";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { getEngagement, getQuestionnaire, saveQuestionnaire, type Questionnaire } from "@/lib/api";

export default function QuestionnairePage() {
  const [data, setData] = useState<Questionnaire | null>(null);
  const [answers, setAnswers] = useState<Record<string, boolean>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [confirmed, setConfirmed] = useState<Record<string, boolean>>({});

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const engagement = await getEngagement();
        const questionnaire = await getQuestionnaire(engagement.id);
        if (!active) return;
        setData(questionnaire);
        setConfirmed(Object.fromEntries(questionnaire.questions.map((question) => [question.itemId, Boolean(question.representation)])));
        setAnswers(Object.fromEntries(questionnaire.questions.filter((question) => question.answer !== null).map((question) => [question.itemId, question.answer as boolean])));
      } catch (caught) {
        if (active) setError(caught instanceof Error ? caught.message : "Could not load the questionnaire.");
      }
    }
    void load();
    return () => { active = false; };
  }, []);

  async function save() {
    if (!data) return;
    setBusy(true);
    setError("");
    setSaved(false);
    try {
      const updated = await saveQuestionnaire(
        data.engagementId,
        Object.entries(answers).map(([itemId, applies]) => ({ itemId, applies, representation: !applies && confirmed[itemId] ? "no_activity" : undefined })),
      );
      setData(updated);
      setSaved(true);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save your answers.");
    } finally {
      setBusy(false);
    }
  }

  if (error && !data) return <p className="text-sm text-red-400">Couldn&apos;t load the questionnaire: {error}</p>;
  if (!data) return <Skeleton className="h-72 w-full" />;

  const unanswered = data.questions.filter((question) => answers[question.itemId] === undefined || (answers[question.itemId] === false && question.whenNo === "representation_required" && !confirmed[question.itemId])).length;
  return (
    <>
      <PageHeader title="Firm questionnaire" description="Answer these yes-or-no questions so we only request documents that apply to your firm. Quinton reviews every N/A answer." />
      <div className="grid gap-4">
        {data.questions.length === 0 ? (
          <Card><CardContent className="pt-5 text-sm text-muted">No conditional checklist items need an answer.</CardContent></Card>
        ) : data.questions.map((question) => (
          <Card key={question.itemId}>
            <CardHeader>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <CardTitle>{question.question}</CardTitle>
                {question.naReviewState === "pending" ? <Badge variant="warning">N/A awaiting Quinton</Badge> : null}
                {question.naReviewState === "approved" ? <Badge variant="success">N/A approved</Badge> : null}
                {question.naReviewState === "rejected" ? <Badge variant="danger">Applies — upload required</Badge> : null}
              </div>
              <CardDescription>{question.sectionTitle}</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              <Button variant={answers[question.itemId] === true ? "default" : "outline"} onClick={() => setAnswers((current) => ({ ...current, [question.itemId]: true }))}>Yes, this applies</Button>
              <Button variant={answers[question.itemId] === false ? "default" : "outline"} onClick={() => setAnswers((current) => ({ ...current, [question.itemId]: false }))}>No — auditor review</Button>
              {answers[question.itemId] === false && question.whenNo === "representation_required" && <label className="flex w-full items-start gap-2 pt-2 text-sm"><input type="checkbox" checked={Boolean(confirmed[question.itemId])} onChange={(event) => setConfirmed((current) => ({ ...current, [question.itemId]: event.target.checked }))} />I confirm the firm had no activity of this type during the review period.</label>}
            </CardContent>
          </Card>
        ))}
      </div>
      {data.questions.length ? (
        <div className="mt-5 flex flex-wrap items-center gap-3">
          <Button disabled={busy || unanswered > 0} onClick={() => void save()}>{busy ? "Saving…" : "Save answers"}</Button>
          {unanswered ? <p className="text-sm text-muted">Answer all {unanswered} remaining question{unanswered === 1 ? "" : "s"}.</p> : null}
          {saved ? <p role="status" className="text-sm text-green-400">Answers saved. <Link href="/checklist" className="underline">View applicable requests</Link></p> : null}
          {error ? <p className="text-sm text-red-400">{error}</p> : null}
        </div>
      ) : null}
    </>
  );
}
