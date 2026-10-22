"use client";

import Link from "next/link";
import { useState } from "react";
import { CalendarDays, CheckSquare2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type TaskPriority = "high" | "normal" | "low";

type AuditorTask = {
  id: string;
  title: string;
  requestId: string;
  due: string;
  priority: TaskPriority;
  assignee: string;
  href: string;
};

const syntheticTasks: AuditorTask[] = [
  {
    id: "task-review-program",
    title: "Review newly uploaded program evidence",
    requestId: "AML-BD-001",
    due: "Today",
    priority: "high",
    assignee: "Quinton",
    href: "/auditor/engagements/eng-synthetic-001",
  },
  {
    id: "task-missing-pages",
    title: "Check replacement for missing pages",
    requestId: "AML-BD-009",
    due: "Tomorrow",
    priority: "high",
    assignee: "Quinton",
    href: "/auditor/engagements/eng-synthetic-001",
  },
  {
    id: "task-applicability",
    title: "Resolve applicability representation",
    requestId: "AML-BD-026",
    due: "Nov 5",
    priority: "normal",
    assignee: "Quinton",
    href: "/auditor/engagements/eng-synthetic-001",
  },
  {
    id: "task-status-update",
    title: "Prepare engagement status update",
    requestId: "Example Securities LLC",
    due: "Nov 7",
    priority: "low",
    assignee: "Quinton",
    href: "/auditor/engagements/eng-synthetic-001",
  },
];

const priorityStyles: Record<TaskPriority, string> = {
  high: "bg-danger",
  normal: "bg-warning",
  low: "bg-info",
};

export function AuditorUpcomingTasks() {
  const [completed, setCompleted] = useState<string[]>([]);
  const openCount = syntheticTasks.length - completed.length;

  function toggleTask(taskId: string) {
    setCompleted((current) =>
      current.includes(taskId)
        ? current.filter((id) => id !== taskId)
        : [...current, taskId],
    );
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
          <ul className="divide-y divide-border">
            {syntheticTasks.map((task) => {
              const isComplete = completed.includes(task.id);
              return (
                <li key={task.id} className="flex gap-3 px-4 py-4">
                  <input
                    type="checkbox"
                    checked={isComplete}
                    onChange={() => toggleTask(task.id)}
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
                      href={task.href}
                      className="mt-1 block truncate text-xs font-medium text-brand-hover hover:underline"
                    >
                      {task.requestId}
                    </Link>
                    <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-subtle">
                      <span className="inline-flex items-center gap-1">
                        <CalendarDays className="size-3" aria-hidden="true" />
                        {task.due}
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
        </CardContent>
      </Card>
      <p className="mt-2 text-[11px] text-subtle">
        Synthetic internal tasks. Completion never finalizes a finding.
      </p>
    </section>
  );
}
