"use client";

import { useState } from "react";
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

type PipelineStage =
  | "intake"
  | "collection"
  | "review"
  | "drafting"
  | "signature"
  | "complete";

type PipelineEngagement = {
  id: string;
  firm: string;
  stage: PipelineStage;
  due: string;
  assignee: string;
  progress: number;
  blockers: number;
  nextAction: string;
};

const stages: { id: PipelineStage; label: string; description: string }[] = [
  { id: "intake", label: "Intake", description: "Scoping and setup" },
  {
    id: "collection",
    label: "Document collection",
    description: "Client evidence gathering",
  },
  { id: "review", label: "Auditor review", description: "Human assessment" },
  {
    id: "drafting",
    label: "Report drafting",
    description: "Prepare auditor draft",
  },
  {
    id: "signature",
    label: "Awaiting signature",
    description: "Explicit auditor action",
  },
  { id: "complete", label: "Complete", description: "Closed engagements" },
];

const initialEngagements: PipelineEngagement[] = [
  {
    id: "eng-synthetic-002",
    firm: "Northstar Brokerage Inc. (synthetic)",
    stage: "intake",
    due: "Dec 18",
    assignee: "Quinton",
    progress: 8,
    blockers: 0,
    nextAction: "Confirm review period and applicable business lines",
  },
  {
    id: "eng-synthetic-001",
    firm: "Example Securities LLC (synthetic)",
    stage: "collection",
    due: "Dec 15",
    assignee: "Quinton",
    progress: 41,
    blockers: 2,
    nextAction: "Receive two replacement documents",
  },
  {
    id: "eng-synthetic-003",
    firm: "Meridian Capital Markets (synthetic)",
    stage: "collection",
    due: "Dec 22",
    assignee: "Quinton",
    progress: 56,
    blockers: 1,
    nextAction: "Complete remaining questionnaire representations",
  },
  {
    id: "eng-synthetic-004",
    firm: "Harborview Securities (synthetic)",
    stage: "review",
    due: "Nov 26",
    assignee: "Quinton",
    progress: 74,
    blockers: 3,
    nextAction: "Resolve three evidence assessments",
  },
  {
    id: "eng-synthetic-005",
    firm: "Summit BD Partners (synthetic)",
    stage: "drafting",
    due: "Nov 14",
    assignee: "Quinton",
    progress: 88,
    blockers: 0,
    nextAction: "Prepare draft for credentialed auditor review",
  },
  {
    id: "eng-synthetic-006",
    firm: "Cedar Ridge Financial (synthetic)",
    stage: "signature",
    due: "Nov 8",
    assignee: "Quinton",
    progress: 97,
    blockers: 0,
    nextAction: "Quinton reviews and explicitly signs the report",
  },
  {
    id: "eng-synthetic-007",
    firm: "Bluewater Securities Group (synthetic)",
    stage: "complete",
    due: "Oct 17",
    assignee: "Quinton",
    progress: 100,
    blockers: 0,
    nextAction: "No open action",
  },
];

function stageLabel(stage: PipelineStage) {
  return stages.find((candidate) => candidate.id === stage)?.label ?? stage;
}

export function AuditorPipelineBoard() {
  const [engagements, setEngagements] =
    useState<PipelineEngagement[]>(initialEngagements);
  const [notice, setNotice] = useState("");
  const active = engagements.filter((item) => item.stage !== "complete");
  const blocked = active.filter((item) => item.blockers > 0).length;

  function moveEngagement(engagementId: string, stage: PipelineStage) {
    const engagement = engagements.find((item) => item.id === engagementId);
    if (!engagement || engagement.stage === stage) return;
    setEngagements((current) =>
      current.map((item) =>
        item.id === engagementId ? { ...item, stage } : item,
      ),
    );
    setNotice(
      `${engagement.firm} moved to ${stageLabel(stage)} in this synthetic preview. No report was signed or finalized.`,
    );
  }

  return (
    <>
      <PageHeader
        title="Audit pipeline"
        description="Move synthetic engagements through the independent AML test workflow. Pipeline movement coordinates work; it never signs a report or finalizes a finding."
        badge={<Badge variant="brand">Synthetic preview</Badge>}
      />

      <div className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
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
          value="3"
          hint="Synthetic deadlines within 30 days"
          icon={<CalendarDays className="size-4" />}
        />
        <Stat
          label="Awaiting signature"
          value={engagements.filter((item) => item.stage === "signature").length}
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

      <div
        aria-label="Audit pipeline stages"
        className="-mx-4 overflow-x-auto px-4 pb-5 sm:-mx-8 sm:px-8 xl:-mx-10 xl:px-10"
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
                    <p className="mt-0.5 text-[11px] text-subtle">
                      {stage.description}
                    </p>
                  </div>
                  <span className="grid size-6 place-items-center rounded-full border border-border bg-surface text-[11px] font-semibold text-muted">
                    {cards.length}
                  </span>
                </div>

                <div className="grid gap-3">
                  {cards.map((engagement) => (
                    <Card
                      key={engagement.id}
                      className="p-4 shadow-[0_8px_24px_-20px_rgba(16,24,40,0.35)]"
                    >
                      <div className="flex items-start gap-2">
                        <div className="min-w-0 flex-1">
                          <h3 className="text-sm font-semibold leading-5 text-foreground">
                            {engagement.firm}
                          </h3>
                          <p className="mt-1 text-[11px] text-subtle">
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

                      <div className="mt-4 flex items-center justify-between text-[11px] text-subtle">
                        <span>{engagement.progress}% reviewed</span>
                        <span>{engagement.due}</span>
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
                          className="grid size-7 place-items-center rounded-full bg-foreground text-[10px] font-semibold text-background"
                          title={`Assigned to ${engagement.assignee}`}
                        >
                          Q
                        </span>
                      </div>

                      <div className="mt-4 border-t border-border pt-3">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-subtle">
                          Next action
                        </p>
                        <p className="mt-1 text-xs leading-5 text-muted">
                          {engagement.nextAction}
                        </p>
                      </div>

                      <label className="mt-4 block text-[11px] font-medium text-muted">
                        Move stage
                        <Select
                          className="mt-1 h-8 text-xs"
                          aria-label={`Move ${engagement.firm} to stage`}
                          value={engagement.stage}
                          onChange={(event) =>
                            moveEngagement(
                              engagement.id,
                              event.target.value as PipelineStage,
                            )
                          }
                        >
                          {stages.map((candidate) => (
                            <option key={candidate.id} value={candidate.id}>
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
      </div>
    </>
  );
}
