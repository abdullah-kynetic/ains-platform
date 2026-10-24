"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { CalendarDays, CheckSquare2, Pencil, Plus } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import {
  createAuditorTask,
  getAuditorTasks,
  setAuditorTaskCompletion,
  updateAuditorTask,
  type AuditorTask,
  type ClientSummary,
  type TaskInput,
  type TaskPriority,
} from "@/lib/workflow-api";

const priorityStyles: Record<TaskPriority, string> = {
  high: "bg-danger",
  normal: "bg-warning",
  low: "bg-info",
};

const emptyDraft: TaskInput = { title: "", requestId: null, due: null, priority: "normal" };

export function AuditorUpcomingTasks({ engagements }: { engagements: ClientSummary[] }) {
  const [tasks, setTasks] = useState<AuditorTask[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [engagementId, setEngagementId] = useState("");
  const [draft, setDraft] = useState<TaskInput>(emptyDraft);
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    getAuditorTasks()
      .then(setTasks)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Unable to load auditor tasks."))
      .finally(() => setLoading(false));
  }, []);
  const openCount = tasks.filter((task) => !task.completed).length;

  function startCreate() {
    setEditingId(null);
    setEngagementId(engagements[0]?.id ?? "");
    setDraft(emptyDraft);
    setError("");
    setShowForm(true);
  }

  function startEdit(task: AuditorTask) {
    setEditingId(task.id);
    setEngagementId(task.engagementId);
    setDraft({ title: task.title, requestId: task.requestId, due: task.due, priority: task.priority });
    setError("");
    setShowForm(true);
  }

  function cancelForm() {
    setShowForm(false);
    setEditingId(null);
    setDraft(emptyDraft);
  }

  async function saveTask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft.title.trim() || !engagementId) return;
    setSaving(true);
    setError("");
    try {
      const input = { ...draft, title: draft.title.trim(), requestId: draft.requestId?.trim() || null };
      if (editingId) {
        const updated = await updateAuditorTask(editingId, input);
        setTasks((current) => current.map((task) => task.id === editingId ? updated : task));
      } else {
        const created = await createAuditorTask(engagementId, input);
        setTasks((current) => [...current, created]);
      }
      cancelForm();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to save this task.");
    } finally {
      setSaving(false);
    }
  }

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
        <Button size="sm" variant="outline" onClick={startCreate} disabled={!engagements.length}>
          <Plus aria-hidden="true" /> Add task
        </Button>
      </div>
      <Card>
        <CardContent className="px-0 pt-1 pb-1">
          {showForm ? (
            <form onSubmit={saveTask} className="mx-4 my-3 grid gap-3 rounded-lg border border-border bg-elevated/40 p-3">
              <p className="text-xs font-semibold text-foreground">{editingId ? "Edit task" : "New internal task"}</p>
              {!editingId ? (
                <label className="grid gap-1 text-xs font-medium text-muted">
                  Engagement
                  <Select aria-label="Task engagement" value={engagementId} onChange={(event) => setEngagementId(event.target.value)} required>
                    {engagements.map((engagement) => <option key={engagement.id} value={engagement.id}>{engagement.firmName}</option>)}
                  </Select>
                </label>
              ) : null}
              <label className="grid gap-1 text-xs font-medium text-muted">
                Task title
                <Input aria-label="Task title" value={draft.title} onChange={(event) => setDraft((current) => ({ ...current, title: event.target.value }))} required maxLength={255} />
              </label>
              <label className="grid gap-1 text-xs font-medium text-muted">
                Request ID (optional)
                <Input aria-label="Task request ID" value={draft.requestId ?? ""} onChange={(event) => setDraft((current) => ({ ...current, requestId: event.target.value || null }))} maxLength={120} placeholder="AML-BD-001" />
              </label>
              <div className="grid grid-cols-2 gap-2">
                <label className="grid gap-1 text-xs font-medium text-muted">
                  Due date
                  <Input aria-label="Task due date" type="date" value={draft.due ?? ""} onChange={(event) => setDraft((current) => ({ ...current, due: event.target.value || null }))} />
                </label>
                <label className="grid gap-1 text-xs font-medium text-muted">
                  Priority
                  <Select aria-label="Task priority" value={draft.priority} onChange={(event) => setDraft((current) => ({ ...current, priority: event.target.value as TaskPriority }))}>
                    <option value="high">High</option>
                    <option value="normal">Normal</option>
                    <option value="low">Low</option>
                  </Select>
                </label>
              </div>
              <div className="flex justify-end gap-2">
                <Button size="sm" variant="ghost" onClick={cancelForm} disabled={saving}>Cancel</Button>
                <Button size="sm" type="submit" disabled={saving || !draft.title.trim() || !engagementId}>{saving ? "Saving…" : "Save task"}</Button>
              </div>
            </form>
          ) : null}
          {loading ? <p role="status" className="px-4 py-8 text-center text-xs text-subtle">Loading upcoming tasks…</p> : null}
          {error ? <p role="alert" className="status-note mx-[var(--space-4)] my-[var(--space-3)]" data-tone="danger">{error}</p> : null}
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
                    <div className="flex items-start gap-2">
                      <p className={cn("min-w-0 flex-1 text-sm font-medium leading-5 text-foreground", isComplete && "text-subtle line-through")}>{task.title}</p>
                      <Button variant="ghost" size="icon-sm" aria-label={`Edit ${task.title}`} onClick={() => startEdit(task)}>
                        <Pencil aria-hidden="true" />
                      </Button>
                    </div>
                    <Link
                      href={`/auditor/engagements/${task.engagementId}`}
                      className="mt-1 block truncate text-xs font-medium text-brand-hover hover:underline"
                    >
                      {task.requestId ?? "Engagement task"}
                    </Link>
                    <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-subtle">
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
                    <p className="mt-2 text-xs text-subtle">
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
      <p className="mt-2 text-xs text-subtle">
        Synthetic internal tasks. Completion never finalizes a finding.
      </p>
    </section>
  );
}
