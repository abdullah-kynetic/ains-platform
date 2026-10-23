"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { CalendarDays, CheckSquare2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { getAuditorTasks, setAuditorTaskCompletion, type AuditorTask, type TaskPriority } from "@/lib/workflow-api";

const priorityStyles: Record<TaskPriority, string> = {
  high: "bg-danger",
  normal: "bg-warning",
  low: "bg-info",
};

export function AuditorUpcomingTasks() {
  const [tasks, setTasks] = useState<AuditorTask[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    getAuditorTasks()
      .then(setTasks)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Unable to load auditor tasks."))
      .finally(() => setLoading(false));
  }, []);
  const openCount = tasks.filter((task) => !task.completed).length;

  async function toggleTask(task: AuditorTask) {
    setError("");
    try {
      await setAuditorTaskCompletion(task.id, !task.completed);
      setTasks((current) => current.map((item) => item.id === task.id ? { ...item, completed: !item.completed } : item));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to update this task.");
    }
  }

  return (
    <section aria-labelledby="auditor-tasks-title">
      <div className="mb-3 flex items-center gap-2.5">
        <CheckSquare2 className="size-4 text-subtle" aria-hidden="true" />
        <h2
          id="auditor-tasks-title"
          className="flex-1 text-sm font-semibold text-foreground"
        >
          Upcoming tasks
        </h2>
        <Badge>{openCount} open</Badge>
      </div>
      <Card>
        <CardContent className="px-0 pt-1 pb-1">
          {loading ? <p role="status" className="px-4 py-8 text-center text-xs text-subtle">Loading upcoming tasks…</p> : null}
          {error ? <p role="alert" className="mx-4 my-3 rounded-lg border border-danger/20 bg-danger/5 px-3 py-2 text-xs text-danger">{error}</p> : null}
          <ul className="divide-y divide-border">
            {tasks.map((task) => {
              const isComplete = task.completed;
              return (
                <li key={task.id} className="flex gap-3 px-4 py-4">
                  <input
                    type="checkbox"
                    checked={isComplete}
                    onChange={() => toggleTask(task)}
                    aria-label={`Mark ${task.title} complete`}
                    className="mt-0.5 size-4 shrink-0 accent-[var(--color-brand)]"
                  />
                  <div className="min-w-0 flex-1">
                    <p
                      className={cn(
                        "text-[13px] font-medium leading-5 text-foreground",
                        isComplete && "text-subtle line-through",
                      )}
                    >
                      {task.title}
                    </p>
                    <Link
                      href={`/auditor/engagements/${task.engagementId}`}
                      className="mt-1 block truncate text-xs font-medium text-brand-hover hover:underline"
                    >
                      {task.requestId ?? "Engagement task"}
                    </Link>
                    <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-subtle">
                      <span className="inline-flex items-center gap-1">
                        <CalendarDays className="size-3" aria-hidden="true" />
                        {task.due ? new Date(`${task.due}T00:00:00`).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : "No due date"}
                      </span>
                      <span className="inline-flex items-center gap-1.5">
                        <span
                          aria-hidden="true"
                          className={cn(
                            "size-1.5 rounded-full",
                            priorityStyles[task.priority],
                          )}
                        />
                        {task.priority} priority
                      </span>
                    </div>
                    <p className="mt-2 text-[11px] text-subtle">
                      Assigned to {task.assignee}
                    </p>
                  </div>
                </li>
              );
            })}
          </ul>
          {!loading && !tasks.length ? <p className="px-4 py-8 text-center text-xs text-subtle">No upcoming tasks assigned.</p> : null}
        </CardContent>
      </Card>
      <p className="mt-2 text-[11px] text-subtle">
        Synthetic internal tasks. Completion never finalizes a finding.
      </p>
    </section>
  );
}
