"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/shell/page";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusNote } from "@/components/ui/status-note";
import { Badge } from "@/components/ui/badge";
import { LoadState } from "@/components/ui/load-state";
import {
  getEngagement,
  getQuestionnaire,
  saveQuestionnaire,
  type Questionnaire,
} from "@/lib/api";

export default function QuestionnairePage() {
  const [data, setData] = useState<Questionnaire | null>(null);
  const [answers, setAnswers] = useState<Record<string, boolean>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const engagement = await getEngagement();
        const questionnaire = await getQuestionnaire(engagement.id);
        if (!active) return;
        setData(questionnaire);
        setAnswers(
          Object.fromEntries(
            questionnaire.questions
              .filter((question) => question.answer === true)
              .map((question) => [question.itemId, question.answer as boolean]),
          ),
        );
      } catch (caught) {
        if (active)
          setError(
            caught instanceof Error
              ? caught.message
              : "Could not load the questionnaire.",
          );
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, []);

  async function save() {
    if (!data) return;
    setBusy(true);
    setError("");
    setSaved(false);
    try {
      const updated = await saveQuestionnaire(
        data.engagementId,
        Object.entries(answers).map(([itemId, applies]) => ({
          itemId,
          applies,
        })),
      );
      setData(updated);
      setSaved(true);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Could not save your answers.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (!data)
    return (
      <LoadState
        error={error}
        label="Loading firm questionnaire…"
        retry={() => window.location.reload()}
      />
    );

  const unanswered = data.questions.filter(
    (question) => answers[question.itemId] !== true,
  ).length;
  return (
    <>
      <PageHeader
        title="Firm questionnaire"
        description="Confirm the conditional requests that apply to your firm. To mark one as not applicable, use “Does not apply” on the document checklist and give a reason."
      />
      <div className="grid gap-4">
        {data.questions.length === 0 ? (
          <Card>
            <CardContent className="pt-5 text-sm text-muted">
              No conditional checklist items need an answer.
            </CardContent>
          </Card>
        ) : (
          data.questions.map((question) => (
            <Card key={question.itemId}>
              <CardHeader>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <CardTitle>{question.question}</CardTitle>
                  {question.naReviewState === "pending" ? (
                    <Badge variant="warning">Legacy N/A response</Badge>
                  ) : null}
                  {question.naReviewState === "approved" ? (
                    <Badge variant="success">Marked N/A</Badge>
                  ) : null}
                  {question.naReviewState === "rejected" ? (
                    <Badge variant="danger">Applies — upload required</Badge>
                  ) : null}
                </div>
                <CardDescription>{question.sectionTitle}</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-2">
                <Button
                  disabled={busy}
                  aria-pressed={answers[question.itemId] === true}
                  variant={
                    answers[question.itemId] === true ? "default" : "outline"
                  }
                  onClick={() => {
                    setSaved(false);
                    setAnswers((current) => ({
                      ...current,
                      [question.itemId]: true,
                    }));
                  }}
                >
                  Yes, this applies
                </Button>
                <p className="basis-full text-sm text-muted">
                  Does not apply to your firm? Say so on the{" "}
                  <Link href="/checklist" className="underline">
                    document checklist
                  </Link>{" "}
                  with a reason. Your auditor decides.
                </p>
              </CardContent>
            </Card>
          ))
        )}
      </div>
      {data.questions.length ? (
        <div className="mt-5 flex flex-wrap items-center gap-3">
          <Button disabled={busy || unanswered > 0} onClick={() => void save()}>
            {busy ? "Saving…" : "Save answers"}
          </Button>
          {unanswered ? (
            <p className="text-sm text-muted">
              Answer all {unanswered} remaining question
              {unanswered === 1 ? "" : "s"}.
            </p>
          ) : null}
          {saved ? (
            <StatusNote tone="success" role="status" className="basis-full">
              Answers saved.{" "}
              <Link href="/checklist" className="underline">
                View applicable requests
              </Link>
            </StatusNote>
          ) : null}
          {error ? (
            <StatusNote tone="danger" role="alert" className="basis-full">
              {error}
            </StatusNote>
          ) : null}
        </div>
      ) : null}
    </>
  );
}
