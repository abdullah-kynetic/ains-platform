"use client";

import { useState } from "react";
import { PageHeader } from "@/components/shell/page";
import { useEngagement } from "@/components/checklist/use-engagement";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
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
  itemId: string;
  state: "ready" | "uploading" | "received" | "error";
  error?: string;
  receipt?: UploadReceipt;
};

export default function AuditorUploadCenter() {
  const { data, error, reload } = useEngagement();
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState("");
  const [files, setFiles] = useState<Pending[]>([]);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const items =
    data?.sections
      .flatMap((section) => section.items)
      .filter((item) => !item.restricted && item.canUpload !== false) ?? [];
  const filtered = items.filter((item) =>
    `${item.requestId} ${item.title}`
      .toLowerCase()
      .includes(search.toLowerCase()),
  );
  function patch(id: string, changes: Partial<Pending>) {
    setFiles((current) =>
      current.map((file) => (file.id === id ? { ...file, ...changes } : file)),
    );
  }
  async function submit() {
    if (!data) return;
    setBusy(true);
    for (const pending of files.filter((file) => file.state !== "received")) {
      const item = items.find((item) => item.id === pending.itemId);
      const suffix = `.${pending.file.name.split(".").pop()?.toLowerCase()}`;
      if (!item || !item.allowedEvidenceTypes.includes(suffix)) {
        patch(pending.id, {
          state: "error",
          error: "Wrong file type for this request.",
        });
        continue;
      }
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
          pending.itemId,
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
  const selectedRequest = items.find((item) => item.id === selected);
  return (
    <>
      <PageHeader
        title="Upload center"
        description="Choose a request, add files, then confirm their destinations. You can return later."
      />
      <ol
        aria-label="Upload steps"
        className="mb-4 grid grid-cols-1 gap-[var(--space-3)] text-sm leading-snug sm:grid-cols-3"
      >
        {["Choose request", "Confirm files", "Keep receipts"].map(
          (step, index) => (
            <li
              key={step}
              className="rounded-lg border border-border bg-surface p-3"
            >
              <span className="mb-1 block font-mono text-brand-hover">
                0{index + 1}
              </span>
              {step}
            </li>
          ),
        )}
      </ol>
      {USE_MOCKS && (
        <p className="mb-5 text-sm text-muted">
          Files stay on your device; only receipt metadata is saved in this
          browser. Use synthetic documents only.
        </p>
      )}
      {!items.length ? (
        <EmptyState
          icon={Files}
          title="No uploads needed right now"
          description="Pending N/A and restricted requests do not accept portal files. Review your checklist or contact your auditor."
        />
      ) : (
        <div className="grid max-w-4xl gap-4 rounded-xl bg-card p-4 border border-border shadow-card">
          <label className="grid gap-2">
            Search requests
            <Input
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setSelected("");
              }}
              placeholder="Request number or title"
              disabled={busy}
            />
          </label>
          <label className="grid gap-2">
            Request
            <Select
              aria-label="Request"
              value={selected}
              onChange={(event) => setSelected(event.target.value)}
              disabled={busy}
            >
              <option value="">Choose a request</option>
              {filtered.map((item) => (
                <option value={item.id} key={item.id}>
                  {item.requestId}: {item.title}
                </option>
              ))}
            </Select>
          </label>
          {!filtered.length && (
            <p role="status">No matching requests. Try another search.</p>
          )}
          {selectedRequest && (
            <div className="rounded-lg border border-border bg-background/40 p-4">
              <h2 className="font-semibold">{selectedRequest.title}</h2>
              <p className="mt-2 text-sm text-muted">
                {selectedRequest.description}
              </p>
              <p className="mt-2 text-xs text-muted">
                Accepted: {selectedRequest.allowedEvidenceTypes.join(", ")} ·
                Maximum 100 MB per file
              </p>
            </div>
          )}
          <label className="grid gap-2">
            {USE_MOCKS ? "Select synthetic files" : "Select files"}
            <input
              type="file"
              multiple
              disabled={!selected || busy}
              onChange={(event) => {
                const added = Array.from(event.target.files ?? []).map(
                  (file): Pending => ({
                    id: crypto.randomUUID(),
                    file,
                    itemId: selected,
                    state: "ready",
                  }),
                );
                setFiles((current) => [...current, ...added]);
                setConfirmed(false);
                event.target.value = "";
              }}
            />
          </label>
          {!files.length && (
            <EmptyState
              icon={Files}
              title="No files selected yet"
              description="Choose a request above, then select one or several files. Nothing is uploaded until you confirm."
            />
          )}
          {files.length > 0 && (
            <section
              aria-label="Confirm file destinations"
              className="grid gap-3 rounded-xl border border-border p-4"
            >
              <h2 className="font-semibold">Confirm file destinations</h2>
              {files.map((pending) => (
                <div
                  key={pending.id}
                  className="grid gap-2 border-t border-border pt-3"
                >
                  <p className="break-all font-medium">{pending.file.name}</p>
                  <label className="grid gap-1 text-sm">
                    Destination for {pending.file.name}
                    <Select
                      aria-label={`Destination for ${pending.file.name}`}
                      className="max-w-full"
                      value={pending.itemId}
                      disabled={busy || pending.state === "received"}
                      onChange={(event) => {
                        patch(pending.id, {
                          itemId: event.target.value,
                          state: "ready",
                          error: undefined,
                        });
                        setConfirmed(false);
                      }}
                    >
                      {items.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.requestId}: {item.title}
                        </option>
                      ))}
                    </Select>
                  </label>
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
                      SHA-256: {pending.receipt.sha256}. Receipt confirms
                      storage, not auditor acceptance.
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
                I have checked each file’s destination.
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
      )}
    </>
  );
}
