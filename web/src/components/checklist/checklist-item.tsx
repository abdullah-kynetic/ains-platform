"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { setRequestNA } from "@/lib/workflow-api";
import { AlertCircle, FileText, Lock } from "lucide-react";
import { StatusBadge } from "./status-badge";
import { STATUS_META, type ChecklistItem } from "@/lib/checklist";
import { formatBytes, formatDate } from "@/lib/utils";

export function ChecklistItemRow({
  item,
  engagementId,
  onChanged,
}: {
  item: ChecklistItem;
  engagementId?: string;
  onChanged?: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function toggleNA() {
    if (!engagementId) return;
    setBusy(true);
    setError("");
    try {
      await setRequestNA(
        engagementId,
        item.id,
        item.status !== "not_applicable",
        "client",
      );
      onChanged?.();
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Could not update this request.",
      );
    } finally {
      setBusy(false);
    }
  }
  const restricted = item.restricted;
  const needsAction =
    item.status === "action_needed_reupload" ||
    item.status === "action_needed_more";
  return (
    <div className="grid gap-3 border-t border-border py-4 first:border-t-0">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-xs font-mono text-brand-hover">{item.requestId}</p>
          <p className="content-heading text-sm font-medium">{item.title}</p>
          {item.description ? (
            <p className="reading-prose mt-0.5 text-xs text-muted">{item.description}</p>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={item.status} />
          {engagementId && (
            <Button
              variant="outline"
              size="sm"
              disabled={busy}
              onClick={() => void toggleNA()}
              aria-label={`${item.status === "not_applicable" ? "Undo N/A" : "Mark N/A"} ${item.requestId}`}
            >
              {busy
                ? "Saving…"
                : item.status === "not_applicable"
                  ? "Undo N/A"
                  : "Mark N/A"}
            </Button>
          )}
        </div>
      </div>

      {error && (
        <p role="alert" className="text-sm text-warning-foreground">
          {error}
        </p>
      )}
      {item.status === "not_applicable" && item.naMarkedByRole && (
        <p className="text-xs text-muted">
          Marked N/A by {item.naMarkedByRole}
        </p>
      )}
      {needsAction && item.reason ? (
        <div className="flex items-start gap-2 rounded-lg border border-warning/20 bg-warning/10 px-3 py-2 text-sm text-warning-foreground">
          <AlertCircle className="mt-0.5 size-4 shrink-0" />
          <span>{item.reason}</span>
        </div>
      ) : null}
      {item.followUp && (
        <p className="text-sm text-warning-foreground">
          Follow-up requested by your auditor.
        </p>
      )}
      {item.naReviewState === "pending" && (
        <p className="text-sm text-muted">
          Legacy N/A response. Use Mark N/A to confirm it directly.
        </p>
      )}

      {restricted ? (
        <div className="flex items-start gap-2 rounded-lg border border-border bg-elevated px-3 py-2 text-sm text-muted">
          <Lock className="mt-0.5 size-4 shrink-0" />
          <span>{STATUS_META.restricted_do_not_upload.help}</span>
        </div>
      ) : null}

      {item.files.length ? (
        <ul className="grid gap-1">
          {item.files.map((f) => (
            <li
              key={f.id}
              className="flex flex-wrap items-center gap-2 text-xs text-muted"
            >
              <FileText className="size-3.5" />
              <span className="truncate">{f.name}</span>
              {f.feedback && (
                <span className="text-warning-foreground">{f.feedback}</span>
              )}
              <span className="text-subtle">
                · {formatBytes(f.size)} · {formatDate(f.uploadedAt)}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
