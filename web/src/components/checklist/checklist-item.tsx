"use client";
import { AlertCircle, FileText, Lock } from "lucide-react";
import { StatusBadge } from "./status-badge";
import { UploadDropzone } from "./upload-dropzone";
import { STATUS_META, UPLOADABLE, type ChecklistItem } from "@/lib/checklist";
import { formatBytes, formatDate } from "@/lib/utils";

export function ChecklistItemRow({ item, onUpload }: { item: ChecklistItem; onUpload: (itemId: string, file: File, onProgress: (pct: number) => void) => Promise<void> }) {
  const restricted = item.status === "restricted_do_not_upload";
  const needsAction = item.status === "action_needed_reupload" || item.status === "action_needed_more";
  return (
    <div className="grid gap-3 border-t border-border py-4 first:border-t-0">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-medium">{item.title}</p>
          {item.description ? <p className="mt-0.5 text-xs text-muted">{item.description}</p> : null}
        </div>
        <StatusBadge status={item.status} />
      </div>

      {needsAction && item.reason ? (
        <div className="flex items-start gap-2 rounded-lg border border-warning/20 bg-warning/10 px-3 py-2 text-sm text-warning-foreground">
          <AlertCircle className="mt-0.5 size-4 shrink-0" />
          <span>{item.reason}</span>
        </div>
      ) : null}

      {restricted ? (
        <div className="flex items-start gap-2 rounded-lg border border-border bg-elevated px-3 py-2 text-sm text-muted">
          <Lock className="mt-0.5 size-4 shrink-0" />
          <span>{STATUS_META.restricted_do_not_upload.help}</span>
        </div>
      ) : null}

      {item.files.length ? (
        <ul className="grid gap-1">
          {item.files.map((f) => (
            <li key={f.id} className="flex items-center gap-2 text-xs text-muted">
              <FileText className="size-3.5" />
              <span className="truncate">{f.name}</span>
              <span className="text-subtle">· {formatBytes(f.size)} · {formatDate(f.uploadedAt)}</span>
            </li>
          ))}
        </ul>
      ) : null}

      {UPLOADABLE.has(item.status) ? (
        <UploadDropzone compact onUpload={(file, p) => onUpload(item.id, file, p)} />
      ) : null}
    </div>
  );
}
