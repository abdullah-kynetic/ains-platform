"use client";
import Link from "next/link";
import { PageHeader, Stat } from "@/components/shell/page";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { LoadState } from "@/components/ui/load-state";
import { buttonVariants } from "@/components/ui/button";
import { StatusBadge } from "@/components/checklist/status-badge";
import { useEngagement } from "@/components/checklist/use-engagement";
import { countByStatus, progressOf } from "@/lib/checklist";
import { USE_MOCKS } from "@/lib/api";
import { formatDate } from "@/lib/utils";

export default function OverviewPage() {
  const { data, error, reload } = useEngagement();
  if (error || !data) return <LoadState error={error} retry={reload} />;
  const p = progressOf(data);
  const c = countByStatus(data);
  const actions = data.sections
    .flatMap((s) => s.items)
    .filter(
      (i) => i.status.startsWith("action_needed") || i.status === "requested",
    );
  return (
    <>
      <PageHeader
        title={data.firmName}
        description={`${data.engagementType} · Review period ${formatDate(data.reviewPeriod.start)} to ${formatDate(data.reviewPeriod.end)}`}
        actions={
          <Link href="/checklist" className={buttonVariants()}>
            Open checklist
          </Link>
        }
      />
      {USE_MOCKS ? (
        <p className="mb-4 text-xs text-subtle">Showing synthetic demo data.</p>
      ) : null}
      <Card className="mb-5">
        <CardHeader>
          <CardTitle>Document progress</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2">
          <Progress value={p.pct} />
          <p className="text-sm text-muted">
            {p.done} of {p.total} requests have file receipts · due{" "}
            {formatDate(data.dueDate)}
          </p>
          <Link href="/questionnaire" className="text-sm underline">
            1. Complete questionnaire
          </Link>
          <Link href="/checklist" className="text-sm underline">
            2. Review applicable requests and pending N/A answers
          </Link>
          <Link href="/upload" className="text-sm underline">
            3. Upload documents or replacements
          </Link>
        </CardContent>
      </Card>
      <div className="mb-5 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="To upload" value={c.requested} />
        <Stat
          label="Action needed"
          value={c.action_needed_reupload + c.action_needed_more}
        />
        <Stat label="Checking" value={c.checking} />
        <Stat
          label="Accepted / with auditor"
          value={c.accepted_for_testing + c.with_auditor}
        />
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Next steps</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2">
          {actions.length ? (
            actions.map((i) => (
              <div
                key={i.id}
                className="flex items-center justify-between gap-3 text-sm"
              >
                <span className="truncate">{i.title}</span>
                <StatusBadge status={i.status} />
              </div>
            ))
          ) : (
            <p className="text-sm text-muted">
              Nothing needed from you right now.
            </p>
          )}
        </CardContent>
      </Card>
    </>
  );
}
