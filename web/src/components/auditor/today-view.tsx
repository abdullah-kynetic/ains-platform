"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  Building2,
  CalendarClock,
  CheckCircle2,
  CheckSquare2,
  ClipboardCheck,
  FileCheck2,
  ListChecks,
  Minus,
  type LucideIcon,
} from "lucide-react";
import { Stat } from "@/components/shell/page";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { cn, formatDate } from "@/lib/utils";
import {
  getAuditorActivity,
  getAuditorTasks,
  getPipeline,
  type AuditorActivity,
  type AuditorTask,
  type ClientSummary,
  type PipelineEngagement,
} from "@/lib/workflow-api";

const DAY = 24 * 60 * 60 * 1000;

function localDate(date = new Date()) {
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 10);
}

function daysUntil(due: string) {
  const [y, m, d] = due.split("-").map(Number);
  const [ty, tm, td] = localDate().split("-").map(Number);
  return Math.round((Date.UTC(y, m - 1, d) - Date.UTC(ty, tm - 1, td)) / DAY);
}

function shortDate(due: string) {
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", timeZone: "UTC" }).format(new Date(due));
}

function dueLabel(due: string) {
  const days = daysUntil(due);
  if (days < 0) return `Overdue ${Math.abs(days)}d`;
  if (days === 0) return "Due today";
  if (days === 1) return "Due tomorrow";
  return `Due in ${days}d`;
}

/** A small change indicator. `good` says whether an increase is an improvement. */
function Change({ value, label, good }: { value: number; label: string; good: "up" | "down" }) {
  const Icon = value === 0 ? Minus : value > 0 ? ArrowUpRight : ArrowDownRight;
  const improved = value === 0 ? null : (value > 0) === (good === "up");
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 text-xs font-medium",
        improved === null && "text-muted",
        improved === true && "text-success-foreground",
        improved === false && "text-danger-foreground",
      )}
    >
      <Icon aria-hidden="true" className="size-3.5" />
      <span className="tabular-nums">{value > 0 ? `+${value}` : value}</span>
      <span className="font-normal text-muted">{label}</span>
    </span>
  );
}

type Row = {
  id: string;
  icon: LucideIcon;
  label: string;
  engagement: string;
  engagementId: string;
  status: { text: string; variant: "danger" | "warning" | "success" | "deadline" };
  due: string | null;
  order: number;
};

export function TodayView({ clients }: { clients: ClientSummary[] }) {
  const [tasks, setTasks] = useState<AuditorTask[] | null>(null);
  const [pipeline, setPipeline] = useState<PipelineEngagement[] | null>(null);
  const [activity, setActivity] = useState<AuditorActivity[]>([]);
  useEffect(() => {
    let active = true;
    getAuditorTasks().then((value) => active && setTasks(value)).catch(() => active && setTasks([]));
    getPipeline().then((value) => active && setPipeline(value)).catch(() => active && setPipeline([]));
    getAuditorActivity().then((value) => active && setActivity(value)).catch(() => active && setActivity([]));
    return () => {
      active = false;
    };
  }, []);

  const names = new Map<string, string>(clients.map((client) => [client.id, client.firmName]));
  for (const entry of pipeline ?? []) names.set(entry.id, entry.firm);
  const openTasks = (tasks ?? []).filter((task) => !task.completed);

  const rows: Row[] = [];
  for (const task of openTasks) {
    if (task.due === null || daysUntil(task.due) > 0) continue;
    const days = daysUntil(task.due);
    rows.push({
      id: `task-${task.id}`,
      icon: CheckSquare2,
      label: task.title,
      engagement: names.get(task.engagementId) ?? "Engagement",
      engagementId: task.engagementId,
      status: days < 0 ? { text: "Overdue", variant: "danger" } : { text: "Due today", variant: "deadline" },
      due: task.due,
      order: days,
    });
  }
  for (const entry of pipeline ?? []) {
    if (entry.stage === "complete" || entry.blockers === 0) continue;
    rows.push({
      id: `blocked-${entry.id}`,
      icon: AlertTriangle,
      label: entry.nextAction,
      engagement: entry.firm,
      engagementId: entry.id,
      status: { text: `${entry.blockers} ${entry.blockers === 1 ? "blocker" : "blockers"}`, variant: "warning" },
      due: entry.due,
      order: entry.due ? daysUntil(entry.due) : 999,
    });
  }
  for (const client of clients) {
    if (!client.readiness.ready) continue;
    rows.push({
      id: `ready-${client.id}`,
      icon: FileCheck2,
      label: "Ready for report drafting. Auditor sign-off required.",
      engagement: client.firmName,
      engagementId: client.id,
      status: { text: "Ready", variant: "success" },
      due: null,
      order: 500,
    });
  }
  rows.sort((a, b) => a.order - b.order);

  const deadlines = [
    ...openTasks
      .filter((task) => task.due !== null && daysUntil(task.due) > 0)
      .map((task) => ({
        id: `task-${task.id}`,
        icon: CheckSquare2,
        label: task.title,
        engagement: names.get(task.engagementId) ?? "Engagement",
        due: task.due as string,
      })),
    ...(pipeline ?? [])
      .filter((entry) => entry.stage !== "complete" && entry.due !== null && daysUntil(entry.due) > 0)
      .map((entry) => ({
        id: `pipeline-${entry.id}`,
        icon: CalendarClock,
        label: "Engagement due",
        engagement: entry.firm,
        due: entry.due as string,
      })),
  ]
    .sort((a, b) => daysUntil(a.due) - daysUntil(b.due))
    .slice(0, 6);

  const recent = (kind: AuditorActivity["kind"]) =>
    activity.filter((item) => item.kind === kind && Date.now() - new Date(item.occurredAt).getTime() <= DAY).length;
  const overdue = rows.filter((row) => row.status.variant === "danger").length;
  const reviewed = clients.reduce((n, c) => n + c.readiness.reviewed, 0);
  const remaining = clients.reduce((n, c) => n + c.readiness.total - c.readiness.reviewed, 0);
  const loading = tasks === null || pipeline === null;
  const total = clients.reduce((n, c) => n + c.readiness.total, 0);

  // Next deadline: the earliest future date across open tasks and engagements still in flight.
  const next = [
    ...openTasks.filter((task) => task.due !== null && daysUntil(task.due) >= 0).map((task) => ({ due: task.due as string, who: names.get(task.engagementId) ?? "Engagement" })),
    ...(pipeline ?? []).filter((entry) => entry.stage !== "complete" && entry.due !== null && daysUntil(entry.due) >= 0).map((entry) => ({ due: entry.due as string, who: entry.firm })),
  ].sort((a, b) => daysUntil(a.due) - daysUntil(b.due))[0];

  // Remaining requests, split by what the engagement is waiting on. Uses only portfolio and pipeline data.
  const blockedIds = new Set((pipeline ?? []).filter((entry) => entry.blockers > 0 && entry.stage !== "complete").map((entry) => entry.id));
  const remainingBlocked = clients.filter((c) => blockedIds.has(c.id)).reduce((n, c) => n + c.readiness.total - c.readiness.reviewed, 0);
  const remainingOther = remaining - remainingBlocked;
  const segments = [
    { key: "reviewed", label: "Reviewed", value: reviewed, className: "bg-success" },
    { key: "blocked", label: "Remaining, engagement blocked", value: remainingBlocked, className: "bg-warning" },
    { key: "other", label: "Remaining", value: remainingOther, className: "bg-border-strong" },
  ];

  return (
    <>
      <section aria-label="Today at a glance" className="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="Next deadline"
          value={loading ? "–" : next ? shortDate(next.due) : "None"}
          icon={<CalendarClock className="size-4" />}
          hint={
            next ? (
              <span className="flex flex-wrap items-center gap-2">
                <Badge variant="deadline">{daysUntil(next.due) === 0 ? "Due today" : `${daysUntil(next.due)} ${daysUntil(next.due) === 1 ? "day" : "days"} left`}</Badge>
                <span className="text-xs text-muted">{next.who}</span>
              </span>
            ) : (
              <span className="text-xs text-muted">{loading ? "Loading…" : "No dated work ahead"}</span>
            )
          }
        />
        <Stat
          label="Needs you today"
          value={loading ? "–" : rows.length}
          icon={<AlertTriangle className="size-4" />}
          hint={<Change value={overdue} label="overdue" good="down" />}
        />
        <Stat
          label="Requests reviewed"
          value={
            <>
              {reviewed} <span className="text-base font-normal text-muted">of {total}</span>
            </>
          }
          icon={<ClipboardCheck className="size-4" />}
          hint={<Change value={recent("review")} label="in the last 24 hours" good="up" />}
        />
        <Stat
          label="Ready for drafting"
          value={clients.filter((c) => c.readiness.ready).length}
          icon={<Building2 className="size-4" />}
          hint={<span className="text-xs text-muted">Auditor sign-off still required</span>}
        />
      </section>

      <section aria-labelledby="still-to-review-title" className="mb-4">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <span className="grid size-8 shrink-0 place-items-center rounded-md bg-elevated text-muted">
                <ListChecks aria-hidden="true" className="size-4" />
              </span>
              <div>
                <CardTitle id="still-to-review-title">Still to review</CardTitle>
                <CardDescription>
                  Requests across your {clients.length} assigned {clients.length === 1 ? "engagement" : "engagements"}
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap items-baseline gap-3">
              <span className="type-metric text-5xl">{remaining}</span>
              <Change value={recent("upload")} label="uploads in the last 24 hours" good="up" />
            </div>
            <div
              role="img"
              aria-label={segments.map((segment) => `${segment.label}: ${segment.value}`).join(". ")}
              className="my-4 flex h-3 gap-0.5 overflow-hidden rounded-full bg-elevated"
            >
              {segments.filter((segment) => segment.value > 0).map((segment) => (
                <span key={segment.key} className={cn("block h-full", segment.className)} style={{ width: `${(segment.value / Math.max(total, 1)) * 100}%` }} />
              ))}
            </div>
            <ul className="grid gap-2 text-xs text-muted sm:grid-cols-3">
              {segments.map((segment) => (
                <li key={segment.key} className="flex items-center gap-2">
                  <span aria-hidden="true" className={cn("size-2 rounded-sm", segment.className)} />
                  {segment.label} <span className="font-medium tabular-nums text-foreground">{segment.value}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </section>

      <div className="mb-6 grid items-start gap-4 xl:grid-cols-[minmax(0,2.3fr)_minmax(300px,1fr)]">
        <section aria-labelledby="needs-you-title" className="min-w-0">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between gap-3">
                <CardTitle id="needs-you-title">Needs you today</CardTitle>
                <Badge>{loading ? "Loading" : `${rows.length} open`}</Badge>
              </div>
              <CardDescription>Overdue and due-today tasks, blocked engagements and work ready for you.</CardDescription>
            </CardHeader>
            <CardContent className="px-0">
              {rows.length === 0 && !loading ? (
                <p role="status" className="flex items-center justify-center gap-2 px-5 py-10 text-sm text-muted">
                  <CheckCircle2 aria-hidden="true" className="size-4 text-success-foreground" />
                  Nothing needs you today.
                </p>
              ) : (
                <div className="px-5">
                  <Table bare>
                    <caption className="sr-only">Items that need you today</caption>
                    <THead>
                      <TR>
                        <TH>Item</TH>
                        <TH>Engagement</TH>
                        <TH>Status</TH>
                        <TH>Due</TH>
                        <TH>
                          <span className="sr-only">Open</span>
                        </TH>
                      </TR>
                    </THead>
                    <TBody>
                      {rows.map((row) => {
                        const Icon = row.icon;
                        return (
                          <TR key={row.id}>
                            <TD>
                              <span className="flex items-center gap-2.5">
                                <span className="grid size-7 shrink-0 place-items-center rounded-md bg-elevated text-muted">
                                  <Icon aria-hidden="true" className="size-4" />
                                </span>
                                <span className="font-medium">{row.label}</span>
                              </span>
                            </TD>
                            <TD className="text-muted">{row.engagement}</TD>
                            <TD>
                              <Badge variant={row.status.variant} dot>
                                {row.status.text}
                              </Badge>
                            </TD>
                            <TD className="whitespace-nowrap text-muted">{row.due ? formatDate(row.due) : "–"}</TD>
                            <TD>
                              <Link
                                href={`/auditor/engagements/${row.engagementId}`}
                                aria-label={`Open ${row.engagement}`}
                                className={buttonVariants({ variant: "outline", size: "sm" })}
                              >
                                Open
                              </Link>
                            </TD>
                          </TR>
                        );
                      })}
                    </TBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </section>

        <section aria-labelledby="deadlines-title" className="min-w-0">
          <Card>
            <CardHeader>
              <CardTitle id="deadlines-title">Upcoming deadlines</CardTitle>
              <CardDescription>The next dates across your engagements.</CardDescription>
            </CardHeader>
            <CardContent>
              {deadlines.length === 0 ? (
                <p role="status" className="py-6 text-center text-sm text-muted">
                  {loading ? "Loading deadlines…" : "No upcoming deadlines."}
                </p>
              ) : (
                <ul className="grid">
                  {deadlines.map((item) => {
                    const Icon = item.icon;
                    return (
                      <li key={item.id} className="flex items-start gap-3 border-t border-border py-3 first:border-t-0 first:pt-0">
                        <span className="mt-0.5 grid size-7 shrink-0 place-items-center rounded-md bg-elevated text-muted">
                          <Icon aria-hidden="true" className="size-4" />
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-medium">{item.label}</span>
                          <span className="block truncate text-xs text-muted">{item.engagement}</span>
                        </span>
                        <Badge variant="deadline" className="shrink-0">
                          {dueLabel(item.due)}
                        </Badge>
                      </li>
                    );
                  })}
                </ul>
              )}
            </CardContent>
          </Card>
        </section>
      </div>
    </>
  );
}
