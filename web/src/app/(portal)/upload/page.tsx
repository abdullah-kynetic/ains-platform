"use client";

import { useState } from "react";
import { PageHeader } from "@/components/shell/page";
import { useEngagement } from "@/components/checklist/use-engagement";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { MAX_UPLOAD_BYTES, uploadDocument, USE_MOCKS, type UploadReceipt } from "@/lib/api";

type Pending = { id: string; file: File; itemId: string; state: "ready" | "uploading" | "received" | "error"; error?: string; receipt?: UploadReceipt };

export default function UploadPage() {
  const { data, error } = useEngagement();
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState("");
  const [files, setFiles] = useState<Pending[]>([]);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const items = data?.sections.flatMap((section) => section.items).filter((item) => !item.restricted) ?? [];
  const filtered = items.filter((item) => `${item.requestId} ${item.title}`.toLowerCase().includes(search.toLowerCase()));
  function patch(id: string, changes: Partial<Pending>) {
    setFiles((current) => current.map((file) => file.id === id ? { ...file, ...changes } : file));
  }
  async function submit() {
    if (!data) return;
    setBusy(true);
    for (const pending of files.filter((file) => file.state !== "received")) {
      const item = items.find((item) => item.id === pending.itemId);
      const suffix = `.${pending.file.name.split(".").pop()?.toLowerCase()}`;
      if (!item || !item.allowedEvidenceTypes.includes(suffix)) {
        patch(pending.id, { state: "error", error: "Wrong file type for this request." }); continue;
      }
      if (pending.file.size > MAX_UPLOAD_BYTES || !pending.file.size) {
        patch(pending.id, { state: "error", error: pending.file.size ? "File is too large (100 MB maximum)." : "File is empty." }); continue;
      }
      patch(pending.id, { state: "uploading", error: undefined });
      try {
        const receipt = await uploadDocument(data.id, pending.itemId, pending.file, () => {});
        patch(pending.id, { state: "received", receipt });
      } catch (error) {
        patch(pending.id, { state: "error", error: error instanceof Error ? error.message : "Upload failed. Try again." });
      }
    }
    setBusy(false);
  }
  if (error) return <p role="alert">Could not load requests: {error}</p>;
  if (!data) return <p role="status">Loading upload center…</p>;
  return <>
    <PageHeader title="Upload center" description="Choose a request, add files, then confirm their destinations. You can return later." />
    {USE_MOCKS && <p className="mb-5 rounded-lg border border-border p-3 text-sm">Synthetic demo only. Files stay on your device; only receipt metadata is saved in this browser. Do not select real client documents.</p>}
    {!items.length ? <p>No requests are accepting portal files.</p> : <div className="grid max-w-4xl gap-5">
      <label className="grid gap-2">Search requests<Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Request number or title" disabled={busy} /></label>
      <label className="grid gap-2">Request<select aria-label="Request" className="rounded-lg border border-border bg-surface p-3" value={selected} onChange={(event) => setSelected(event.target.value)} disabled={busy}>
        <option value="">Choose a request</option>
        {filtered.map((item) => <option value={item.id} key={item.id}>{item.requestId} — {item.title}</option>)}
      </select></label>
      {!filtered.length && <p role="status">No matching requests. Try another search.</p>}
      <label className="grid gap-2">Select synthetic files<input type="file" multiple disabled={!selected || busy} onChange={(event) => {
        const added = Array.from(event.target.files ?? []).map((file): Pending => ({ id: crypto.randomUUID(), file, itemId: selected, state: "ready" }));
        setFiles((current) => [...current, ...added]); setConfirmed(false); event.target.value = "";
      }} /></label>
      {files.length > 0 && <section aria-label="Confirm file destinations" className="grid gap-3 rounded-xl border border-border p-4">
        <h2 className="font-semibold">Confirm file destinations</h2>
        {files.map((pending) => <div key={pending.id} className="grid gap-2 border-t border-border pt-3">
          <p className="break-all font-medium">{pending.file.name}</p>
          <label className="grid gap-1 text-sm">Destination for {pending.file.name}<select aria-label={`Destination for ${pending.file.name}`} className="max-w-full rounded-lg border border-border bg-surface p-2" value={pending.itemId} disabled={busy || pending.state === "received"} onChange={(event) => { patch(pending.id, { itemId: event.target.value, state: "ready", error: undefined }); setConfirmed(false); }}>
            {items.map((item) => <option key={item.id} value={item.id}>{item.requestId} — {item.title}</option>)}
          </select></label>
          <p role="status">{pending.state === "received" ? "Received" : pending.state === "uploading" ? "Uploading…" : pending.state === "error" ? "Not received" : "Ready to upload"}</p>
          {pending.error && <p role="alert" className="text-red-300">{pending.error}</p>}
          {pending.receipt && <p className="break-all text-xs text-muted">SHA-256: {pending.receipt.sha256}. Receipt confirms storage, not auditor acceptance.</p>}
          {pending.state !== "received" && <Button variant="ghost" disabled={busy} onClick={() => { setFiles((current) => current.filter((file) => file.id !== pending.id)); setConfirmed(false); }}>Remove {pending.file.name}</Button>}
        </div>)}
        <label className="flex items-center gap-2"><input type="checkbox" checked={confirmed} disabled={busy} onChange={(event) => setConfirmed(event.target.checked)} />I have checked each file’s destination.</label>
        <Button disabled={!confirmed || busy || files.every((file) => file.state === "received")} onClick={() => void submit()}>{busy ? "Uploading…" : "Confirm and upload"}</Button>
      </section>}
    </div>}
  </>;
}
