"use client";

import Link from "next/link";
import {
  ArrowUpRight,
  CalendarDays,
  CheckCircle2,
  Clock3,
  FileUp,
  ListTodo,
} from "lucide-react";
import { ChecklistStatus } from "@/components/portal/checklist-status";
import { PageHeader, Stat } from "@/components/shell/page";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { LoadState } from "@/components/ui/load-state";
import { buttonVariants } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/checklist/status-badge";
import { useEngagement } from "@/components/checklist/use-engagement";
import { countByStatus, progressOf } from "@/lib/checklist";
import { USE_MOCKS } from "@/lib/api";
import { formatDate } from "@/lib/utils";

export default function OverviewPage() {
  const { data, error, reload } = useEngagement();

  if (error || !data) return <LoadState error={error} retry={reload} />;

  const progress = progressOf(data);
  const counts = countByStatus(data);
  const actions = data.sections
    .flatMap((section) => section.items)
    .filter(
      (item) =>
        item.status.startsWith("action_needed") ||
        item.status === "requested",
    );

  return (
    <>
      <PageHeader
        title={data.firmName}
        description={`${data.engagementType} · Review period ${formatDate(data.reviewPeriod.start)} to ${formatDate(data.reviewPeriod.end)}`}
        badge={<Badge variant="brand">Active engagement</Badge>}
        actions={
          <Link href="/checklist" className={buttonVariants()}>
            Open checklist <ArrowUpRight />
          </Link>
        }
      />

      <ChecklistStatus engagementId={data.id} />

      {USE_MOCKS ? (
        <div className="mb-[var(--space-5)] flex items-center gap-[var(--space-2)] text-xs leading-snug text-muted">
          <span className="size-1.5 rounded-full bg-success" />
          Synthetic demonstration workspace
        </div>
      ) : null}

      <div className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="To upload"
          value={counts.requested}
          hint="Awaiting client upload"
          icon={<FileUp className="size-4" />}
        />
        <Stat
          label="Action needed"
          value={counts.action_needed_reupload + counts.action_needed_more}
          hint="Document-level follow-up"
          icon={<ListTodo className="size-4" />}
        />
        <Stat
          label="Checking"
          value={counts.checking}
          hint="Intake quality review"
          icon={<Clock3 className="size-4" />}
        />
        <Stat
          label="Ready for testing"
          value={counts.accepted_for_testing + counts.with_auditor}
          hint="Accepted or with auditor"
          icon={<CheckCircle2 className="size-4" />}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.7fr)_minmax(280px,0.8fr)]">
        <Card>
          <CardHeader className="flex-row items-start justify-between gap-4">
            <div>
              <CardTitle>Document readiness</CardTitle>
              <CardDescription>
                Intake progress for the current review period
              </CardDescription>
            </div>
            <span className="text-2xl font-semibold tabular-nums tracking-[-0.04em]">
              {Math.round(progress.pct)}%
            </span>
          </CardHeader>
          <CardContent>
            <Progress value={progress.pct} className="h-2.5" />
            <div className="mt-[var(--space-5)] grid grid-cols-1 divide-y divide-border border-y border-border sm:grid-cols-3 sm:divide-x sm:divide-y-0">
              <div className="px-[var(--space-4)] py-[var(--space-3)] first:pl-0">
                <p className="text-xs font-medium text-muted">
                  Received
                </p>
                <p className="mt-1 text-lg font-semibold tabular-nums">
                  {progress.done}
                </p>
              </div>
              <div className="px-[var(--space-4)] py-[var(--space-3)] first:pl-0">
                <p className="text-xs font-medium text-muted">
                  Total
                </p>
                <p className="mt-1 text-lg font-semibold tabular-nums">
                  {progress.total}
                </p>
              </div>
              <div className="px-[var(--space-4)] py-[var(--space-3)] first:pl-0">
                <p className="text-xs font-medium text-muted">
                  Remaining
                </p>
                <p className="mt-1 text-lg font-semibold tabular-nums">
                  {progress.total - progress.done}
                </p>
              </div>
            </div>
            <div className="mt-5 grid gap-2 text-sm">
              <Link href="/questionnaire" className="text-foreground underline underline-offset-4 hover:text-muted">
                1. Complete questionnaire
              </Link>
              <Link href="/checklist" className="text-foreground underline underline-offset-4 hover:text-muted">
                2. Review requests and mark anything that does not apply
              </Link>
              <Link href="/upload" className="text-foreground underline underline-offset-4 hover:text-muted">
                3. Upload documents or replacements
              </Link>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Engagement timeline</CardTitle>
            <CardDescription>Current client-facing milestone</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            <div className="flex items-start gap-3">
              <span className="grid size-9 shrink-0 place-items-center rounded-md bg-brand-tint text-brand">
                <CalendarDays className="size-4" />
              </span>
              <div>
                <p className="text-sm font-medium">Documents due</p>
                <p className="mt-0.5 text-xs text-muted">
                  {formatDate(data.dueDate)}
                </p>
              </div>
            </div>
            <div className="rounded-lg bg-elevated/70 px-[var(--space-3)] py-[var(--space-3)] text-xs leading-normal text-muted">
              The auditor will review submitted materials after intake checks
              are complete.
            </div>
          </CardContent>
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader className="flex-row items-center justify-between gap-4">
            <div>
              <CardTitle>Next steps</CardTitle>
              <CardDescription>
                Document requests that need attention
              </CardDescription>
            </div>
            <Link
              href="/checklist"
              className={buttonVariants({ variant: "ghost", size: "sm" })}
            >
              View all <ArrowUpRight />
            </Link>
          </CardHeader>
          <CardContent className="grid divide-y divide-border">
            {actions.length ? (
              actions.slice(0, 4).map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">
                      {item.title}
                    </p>
                    <p className="mt-[var(--space-1)] text-xs leading-snug text-muted">
                      Document request
                    </p>
                  </div>
                  <StatusBadge status={item.status} />
                </div>
              ))
            ) : (
              <p className="text-sm text-muted">
                Nothing needed from you right now.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
