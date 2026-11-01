"use client";

import { useState } from "react";
import { useSession } from "@/components/auth/session";
import AuditorUploadCenter from "@/components/checklist/auditor-upload-center";
import { PageHeader } from "@/components/shell/page";
import { useEngagement } from "@/components/checklist/use-engagement";
import { Button } from "@/components/ui/button";
import { LoadState } from "@/components/ui/load-state";
import { EmptyState } from "@/components/ui/empty-state";
import { Files } from "lucide-react";
import {
  MAX_UPLOAD_BYTES,
  uploadDocument,
  USE_MOCKS,
  type UploadReceipt,
} from "@/lib/api";

type Pending = {
  id: string;
  file: File;
  state: "ready" | "uploading" | "received" | "error";
  error?: string;
  receipt?: UploadReceipt;
};

export default function UploadPage() {
  const { session } = useSession();
  return session?.user.role === "auditor" ? (
    <AuditorUploadCenter />
  ) : (
    <ClientUploadCenter />
  );
}

function ClientUploadCenter() {
  const { data, error, reload } = useEngagement();
  const [files, setFiles] = useState<Pending[]>([]);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  function addFiles(selected: File[]) {
    setFiles((current) => [
      ...current,
      ...selected.map((file): Pending => ({
        id: crypto.randomUUID(),
        file,
        state: "ready",
      })),
    ]);
    setConfirmed(false);
  }
  function patch(id: string, changes: Partial<Pending>) {
    setFiles((current) =>
      current.map((file) => (file.id === id ? { ...file, ...changes } : file)),
    );
  }
  async function submit() {
    if (!data) return;
    setBusy(true);
    for (const pending of files.filter((file) => file.state !== "received")) {
      if (pending.file.size > MAX_UPLOAD_BYTES || !pending.file.size) {
        patch(pending.id, {
          state: "error",
          error: pending.file.size
            ? "File is too large (100 MB maximum)."
            : "File is empty.",
        });
        continue;
      }
      patch(pending.id, { state: "uploading", error: undefined });
      try {
        const receipt = await uploadDocument(
          data.id,
          null,
          pending.file,
          () => {},
        );
        patch(pending.id, { state: "received", receipt });
      } catch (error) {
        patch(pending.id, {
          state: "error",
          error:
            error instanceof Error
              ? error.message
              : "Upload failed. Try again.",
        });
      }
    }
    setBusy(false);
  }
  if (error || !data)
    return (
      <LoadState error={error} label="Loading upload center…" retry={reload} />
    );
  return (
    <>
      <PageHeader
        title="Upload center"
        description="Add files for your engagement, then confirm the upload. You can return later."
      />
      <ol
        aria-label="Upload steps"
        className="mb-4 grid grid-cols-1 gap-[var(--space-3)] text-sm leading-snug sm:grid-cols-3"
      >
        {["Add files", "Confirm files", "Keep receipts"].map((step, index) => (
          <li
            key={step}
            className="rounded-lg border border-border bg-surface p-3"
          >
            <span className="mb-1 block font-mono text-brand-hover">
              0{index + 1}
            </span>
            {step}
          </li>
        ))}
      </ol>
      {USE_MOCKS && (
        <p className="mb-5 text-sm text-muted">
          Files stay on your device; only receipt metadata is saved in this
          browser. Use synthetic documents only.
        </p>
      )}
      {!!data.unassignedDocuments?.length && (
        <section
          aria-label="Previous uploads"
          className="mb-5 grid gap-2 text-sm"
        >
          {data.unassignedDocuments.map((document) => (
            <p key={document.id}>
              <span>{document.name}</span> · Received ·{" "}
              <span className="break-all text-xs text-muted">
                SHA-256: {document.sha256}
              </span>
            </p>
          ))}
        </section>
      )}
      <div
        className="grid max-w-4xl gap-4 rounded-xl bg-card p-4 border border-border shadow-card"
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault();
          if (!busy) addFiles(Array.from(event.dataTransfer.files));
        }}
      >
        <p className="text-sm text-muted">
          Drop files here or select multiple files. Files are attached to your
          engagement for auditor review. Do not upload restricted documents.
          Maximum 100 MB per file.
        </p>
        <label className="grid gap-2">
          {USE_MOCKS ? "Select synthetic files" : "Select files"}
          <input
            type="file"
            multiple
            disabled={busy}
            onChange={(event) => {
              addFiles(Array.from(event.target.files ?? []));
              event.target.value = "";
            }}
          />
        </label>
        {!files.length && (
          <EmptyState
            icon={Files}
            title="No files selected yet"
            description="Drop or select one or several files. Nothing is uploaded until you confirm."
          />
        )}
        {files.length > 0 && (
          <section
            aria-label="Confirm files"
            className="grid gap-3 rounded-xl border border-border p-4"
          >
            <h2 className="font-semibold">Confirm files</h2>
            {files.map((pending) => (
              <div
                key={pending.id}
                className="grid gap-2 border-t border-border pt-3"
              >
                <p className="break-all font-medium">{pending.file.name}</p>
                <p role="status">
                  {pending.state === "received"
                    ? "Received"
                    : pending.state === "uploading"
                      ? "Uploading…"
                      : pending.state === "error"
                        ? "Not received"
                        : "Ready to upload"}
                </p>
                {pending.error && (
                  <p role="alert" className="status-note" data-tone="danger">
                    {pending.error}
                  </p>
                )}
                {pending.receipt && (
                  <p className="break-all text-xs text-muted">
                    SHA-256: {pending.receipt.sha256}. Receipt confirms storage,
                    not auditor acceptance.
                  </p>
                )}
                {pending.state !== "received" && (
                  <Button
                    variant="ghost"
                    aria-label={`Remove ${pending.file.name}`}
                    disabled={busy}
                    onClick={() => {
                      setFiles((current) =>
                        current.filter((file) => file.id !== pending.id),
                      );
                      setConfirmed(false);
                    }}
                  >
                    Remove file
                  </Button>
                )}
              </div>
            ))}
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={confirmed}
                disabled={busy}
                onChange={(event) => setConfirmed(event.target.checked)}
              />
              I have checked the files for this engagement.
            </label>
            <Button
              disabled={
                !confirmed ||
                busy ||
                files.every((file) => file.state === "received")
              }
              onClick={() => void submit()}
            >
              {busy ? "Uploading…" : "Confirm and upload"}
            </Button>
          </section>
        )}
      </div>
    </>
  );
}
