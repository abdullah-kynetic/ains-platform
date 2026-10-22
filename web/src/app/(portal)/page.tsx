"use client";
import Link from "next/link";
import { PageHeader, Stat } from "@/components/shell/page";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { buttonVariants } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/checklist/status-badge";
import { useEngagement } from "@/components/checklist/use-engagement";
import { countByStatus, progressOf } from "@/lib/checklist";
import { USE_MOCKS } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { ArrowUpRight, CalendarDays, CheckCircle2, Clock3, FileUp, ListTodo } from "lucide-react";

export default function OverviewPage() {
  const { data, error } = useEngagement();
  if (error) return <p className="text-sm text-danger-foreground">Couldn&apos;t load your engagement: {error}</p>;
  if (!data) return <Skeleton className="h-48 w-full" />;
  const p = progressOf(data);
  const c = countByStatus(data);
  const actions = data.sections.flatMap((s) => s.items).filter((i) => i.status.startsWith("action_needed") || i.status === "requested");
  return (
    <>
      <PageHeader
        title={data.firmName}
        description={`${data.engagementType} · Review period ${formatDate(data.reviewPeriod.start)} to ${formatDate(data.reviewPeriod.end)}`}
        badge={<Badge variant="brand">Active engagement</Badge>}
        actions={<Link href="/checklist" className={buttonVariants()}>Open documents <ArrowUpRight /></Link>}
      />
      {USE_MOCKS ? <div className="mb-5 flex items-center gap-2 text-[11px] text-subtle"><span className="size-1.5 rounded-full bg-success" />Synthetic demonstration workspace</div> : null}

      <div className="mb-6 grid grid-cols-2 gap-3 xl:grid-cols-4">
        <Stat label="To upload" value={c.requested} hint="Awaiting client upload" icon={<FileUp className="size-4" />} />
        <Stat label="Action needed" value={c.action_needed_reupload + c.action_needed_more} hint="Document-level follow-up" icon={<ListTodo className="size-4" />} />
        <Stat label="Checking" value={c.checking} hint="Intake quality review" icon={<Clock3 className="size-4" />} />
        <Stat label="Ready for testing" value={c.accepted_for_testing + c.with_auditor} hint="Accepted or with auditor" icon={<CheckCircle2 className="size-4" />} />
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.7fr)_minmax(280px,0.8fr)]">
        <Card>
          <CardHeader className="flex-row items-start justify-between gap-4">
            <div>
              <CardTitle>Document readiness</CardTitle>
              <CardDescription>Intake progress for the current review period</CardDescription>
            </div>
            <span className="text-2xl font-semibold tabular-nums tracking-[-0.04em]">{Math.round(p.pct)}%</span>
          </CardHeader>
          <CardContent>
            <Progress value={p.pct} className="h-2.5" />
            <div className="mt-5 grid grid-cols-3 divide-x divide-border rounded-lg border border-border bg-background py-3">
              <div className="px-4"><p className="text-[10px] font-medium uppercase tracking-[0.1em] text-subtle">Received</p><p className="mt-1 text-lg font-semibold tabular-nums">{p.done}</p></div>
              <div className="px-4"><p className="text-[10px] font-medium uppercase tracking-[0.1em] text-subtle">Total</p><p className="mt-1 text-lg font-semibold tabular-nums">{p.total}</p></div>
              <div className="px-4"><p className="text-[10px] font-medium uppercase tracking-[0.1em] text-subtle">Remaining</p><p className="mt-1 text-lg font-semibold tabular-nums">{p.total - p.done}</p></div>
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
              <span className="grid size-9 shrink-0 place-items-center rounded-md bg-brand-tint text-brand"><CalendarDays className="size-4" /></span>
              <div><p className="text-sm font-medium">Documents due</p><p className="mt-0.5 text-xs text-muted">{formatDate(data.dueDate)}</p></div>
            </div>
            <div className="rounded-lg border border-border bg-background px-3 py-2.5 text-xs leading-5 text-muted">The auditor will review submitted materials after intake checks are complete.</div>
          </CardContent>
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader className="flex-row items-center justify-between gap-4">
            <div><CardTitle>Next steps</CardTitle><CardDescription>Document requests that need attention</CardDescription></div>
            <Link href="/checklist" className={buttonVariants({ variant: "ghost", size: "sm" })}>View all <ArrowUpRight /></Link>
          </CardHeader>
          <CardContent className="grid gap-1">
            {actions.length ? actions.map((i) => (
              <div key={i.id} className="flex items-center justify-between gap-4 border-t border-border py-3 first:border-t-0">
                <div className="min-w-0"><p className="truncate text-sm font-medium">{i.title}</p><p className="mt-0.5 text-[11px] text-subtle">Document request</p></div>
                <StatusBadge status={i.status} />
              </div>
            )) : <p className="text-sm text-muted">Nothing needed from you right now.</p>}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
