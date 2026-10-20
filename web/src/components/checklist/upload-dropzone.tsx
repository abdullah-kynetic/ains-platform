"use client";
import { useRef, useState } from "react";
import { UploadCloud } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { MAX_UPLOAD_BYTES } from "@/lib/api";
import { cn } from "@/lib/utils";

/** Drag-and-drop (or click) upload for one checklist item, with progress. Adapted from the earlier portal's UploadBox. */
export function UploadDropzone({ onUpload, compact }: { onUpload: (file: File, onProgress: (pct: number) => void) => Promise<void>; compact?: boolean }) {
  const input = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);

  async function send(files: FileList | null | undefined) {
    if (!files?.length) return;
    for (const file of Array.from(files)) {
      setProgress(0);
      try {
        await onUpload(file, setProgress);
        toast.success(`${file.name} uploaded. We'll check it shortly.`);
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Upload failed.");
      }
    }
    setProgress(null);
    if (input.current) input.current.value = "";
  }

  const busy = progress !== null;
  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => { e.preventDefault(); setDrag(false); if (!busy) void send(e.dataTransfer.files); }}
      className={cn(
        "flex flex-col items-center gap-2 rounded-xl border border-dashed text-center transition-colors",
        compact ? "p-4" : "p-6",
        drag ? "border-brand bg-brand-tint" : "border-white/15",
      )}
    >
      {busy ? (
        <div className="grid w-full max-w-sm gap-2">
          <p className="text-sm text-muted">Uploading… {progress}%</p>
          <Progress value={progress ?? 0} />
        </div>
      ) : (
        <>
          <UploadCloud className="size-5 text-muted" />
          <p className="text-sm text-muted">
            Drag files here, or{" "}
            <Button variant="secondary" size="sm" onClick={() => input.current?.click()}>choose files</Button>
          </p>
          <p className="text-xs text-subtle">PDF, images, Office files, CSV. Up to {Math.round(MAX_UPLOAD_BYTES / 1024 / 1024)}&nbsp;MB each.</p>
        </>
      )}
      <input ref={input} type="file" multiple className="hidden" onChange={(e) => void send(e.target.files)} />
    </div>
  );
}
