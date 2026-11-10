"use client";

import { useEffect, useState } from "react";
import {
  AlertTriangle,
  CalendarDays,
  CheckCircle2,
  Clock3,
  Users,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Select } from "@/components/ui/select";
import { PageHeader, Stat } from "@/components/shell/page";
import { LoadState } from "@/components/ui/load-state";
import { USE_MOCKS } from "@/lib/api";
import { getPipeline, movePipelineStage, type PipelineEngagement, type PipelineStage } from "@/lib/workflow-api";

const stages: { id: PipelineStage; label: string; description: string }[] = [
  { id: "intake", label: "Intake", description: "Scoping and setup" },
  {
    id: "document_collection",
    label: "Document collection",
    description: "Client evidence gathering",
  },
  { id: "auditor_review", label: "Auditor review", description: "Human assessment" },
  {
    id: "report_drafting",
    label: "Report drafting",
    description: "Prepare auditor draft",
  },
  {
    id: "awaiting_signature",
    label: "Awaiting signature",
    description: "Explicit auditor action",
  },
  { id: "complete", label: "Complete", description: "Closed engagements" },
];

function stageLabel(stage: PipelineStage) {
  return stages.find((candidate) => candidate.id === stage)?.label ?? stage;
}

export function AuditorPipelineBoard() {
  const [engagements, setEngagements] = useState<PipelineEngagement[]>([]);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [moving, setMoving] = useState<string | null>(null);
  const [asOf] = useState(() => new Date().setHours(0, 0, 0, 0));
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    getPipeline()
      .then(setEngagements)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Unable to load the pipeline."))
      .finally(() => setLoading(false));
  }, []);
  const active = engagements.filter((item) => item.stage !== "complete");
  const blocked = active.filter((item) => item.blockers > 0).length;

  async function moveEngagement(engagementId: string, stage: PipelineStage) {
    const engagement = engagements.find((item) => item.id === engagementId);
    if (!engagement || engagement.stage === stage) return;
    setError("");
    setMoving(engagementId);
    try {
      await movePipelineStage(engagementId, stage);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to move this engagement.");
      return;
    } finally {
      setMoving(null);
    }
    setEngagements((current) =>
      current.map((item) =>
        item.id === engagementId ? { ...item, stage } : item,
      ),
    );
    setNotice(
      `${engagement.firm} moved to ${stageLabel(stage)}${USE_MOCKS ? " in this synthetic preview" : ""}. No report was signed or finalized.`,
    );
  }

  return (
    <>
      <PageHeader
        title="Audit pipeline"
        description="Move engagements through the independent AML test workflow. Pipeline movement coordinates work; it never signs a report or finalizes a finding."
        badge={USE_MOCKS ? <Badge variant="brand">Synthetic preview</Badge> : undefined}
      />

      <div className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="Active engagements"
          value={active.length}
          hint="Across five open workflow stages"
          icon={<Users className="size-4" />}
        />
        <Stat
          label="Blocked"
          value={blocked}
          hint="Needs evidence or a human decision"
          icon={<AlertTriangle className="size-4" />}
        />
        <Stat
          label="Due soon"
          value={active.filter((entry) => {
            if (!entry.due) return false;
            const remaining = new Date(`${entry.due}T00:00:00`).getTime() - asOf;
            return remaining >= 0 && remaining <= 30 * 24 * 60 * 60 * 1000;
          }).length}
          hint="Deadlines within the next 30 days"
          icon={<CalendarDays className="size-4" />}
        />
        <Stat
          label="Awaiting signature"
          value={engagements.filter((item) => item.stage === "awaiting_signature").length}
          hint="Requires explicit auditor action"
          icon={<Clock3 className="size-4" />}
        />
      </div>

      {notice ? (
        <p
          role="status"
          className="mb-4 rounded-lg border border-brand/20 bg-brand-tint px-4 py-3 text-sm text-brand"
        >
          {notice}
        </p>
      ) : null}

      {error ? <p role="alert" className="status-note mb-[var(--space-4)]" data-tone="danger">{error}</p> : null}
      {loading ? <LoadState label="Loading audit pipeline…" /> : null}

      {!loading ? <div
        aria-label="Audit pipeline stages"
        className="-mx-4 overflow-x-auto px-4 pb-4 md:-mx-6 md:px-6"
      >
        <div className="grid min-w-[1800px] grid-cols-6 items-start gap-4">
          {stages.map((stage) => {
            const cards = engagements.filter((item) => item.stage === stage.id);
            return (
              <section
                key={stage.id}
                aria-labelledby={`pipeline-${stage.id}`}
                className="rounded-xl border border-border bg-elevated/60 p-3"
              >
                <div className="mb-3 flex items-start gap-2 px-1">
                  <div className="min-w-0 flex-1">
                    <h2
                      id={`pipeline-${stage.id}`}
                      className="text-sm font-semibold text-foreground"
                    >
                      {stage.label}
                    </h2>
                    <p className="mt-0.5 text-xs text-subtle">
                      {stage.description}
                    </p>
                  </div>
                  <span className="grid size-6 place-items-center rounded-full border border-border bg-surface text-xs font-semibold text-muted">
                    {cards.length}
                  </span>
                </div>

                <div className="grid gap-3">
                  {cards.map((engagement) => (
                    <Card
                      key={engagement.id}
                      className="p-4 shadow-pop"
                    >
                      <div className="flex items-start gap-2">
                        <div className="min-w-0 flex-1">
                          <h3 className="content-heading text-sm font-semibold leading-5 text-foreground">
                            {engagement.firm}
                          </h3>
                          <p className="mt-1 text-xs text-subtle">
                            FINRA Rule 3310 independent AML test
                          </p>
                        </div>
                        {engagement.stage === "complete" ? (
                          <CheckCircle2
                            className="size-4 shrink-0 text-success-foreground"
                            aria-label="Workflow complete"
                          />
                        ) : null}
                      </div>

                      <div className="mt-4 flex items-center justify-between text-xs text-subtle">
                        <span>{engagement.progress}% reviewed</span>
                        <span>{engagement.due ? new Date(`${engagement.due}T00:00:00`).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : "No due date"}</span>
                      </div>
                      <Progress
                        value={engagement.progress}
                        className="mt-2 h-1.5"
                        label={`${engagement.firm} review progress`}
                      />

                      <div className="mt-4 flex items-center justify-between gap-2">
                        {engagement.blockers ? (
                          <Badge variant="warning" dot>
                            {engagement.blockers} blocker
                            {engagement.blockers === 1 ? "" : "s"}
                          </Badge>
                        ) : (
                          <Badge variant="success" dot>
                            Clear
                          </Badge>
                        )}
                        <span
                          className="grid size-7 place-items-center rounded-full bg-foreground text-xs font-semibold text-background"
                          title={`Assigned to ${engagement.assignee}`}
                        >
                          {engagement.assignee.split(" ").filter(Boolean).map((part) => part[0]).slice(0, 2).join("") || "—"}
                        </span>
                      </div>

                      <div className="mt-4 border-t border-border pt-3">
                        <p className="text-xs font-semibold uppercase tracking-[0.1em] text-subtle">
                          Next action
                        </p>
                        <p className="mt-1 text-xs leading-5 text-muted">
                          {engagement.nextAction}
                        </p>
                      </div>

                      <label className="mt-4 block text-xs font-medium text-muted">
                        Move stage
                        <Select
                          className="mt-[var(--space-2)]"
                          aria-label={`Move ${engagement.firm} to stage`}
                          value={engagement.stage}
                          disabled={moving === engagement.id}
                          onChange={(event) =>
                            moveEngagement(
                              engagement.id,
                              event.target.value as PipelineStage,
                            )
                          }
                        >
                          {stages.map((candidate) => (
                            <option key={candidate.id} value={candidate.id} disabled={candidate.id === "complete" && engagement.stage !== "complete"}>
                              {candidate.label}
                            </option>
                          ))}
                        </Select>
                      </label>
                    </Card>
                  ))}
                  {!cards.length ? (
                    <div className="rounded-lg border border-dashed border-border-strong px-3 py-8 text-center text-xs text-subtle">
                      No engagements in this stage
                    </div>
                  ) : null}
                </div>
              </section>
            );
          })}
        </div>
      </div> : null}
    </>
  );
}
