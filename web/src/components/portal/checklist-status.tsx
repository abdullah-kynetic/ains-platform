"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { getProgress, STAGE_LABEL, type Progress } from "@/lib/api/flow";
import { formatDate } from "@/lib/utils";

/** Step 2, client side: whether the auditor has sent the checklist, and where the audit stands. */
export function ChecklistStatus({ engagementId, onLoad }: { engagementId: string; onLoad?: (p: Progress) => void }) {
  const [progress, setProgress] = useState<Progress | null>(null);
  useEffect(() => {
    let alive = true;
    getProgress(engagementId, "client")
      .then((p) => { if (alive) { setProgress(p); onLoad?.(p); } })
      .catch(() => undefined);
    return () => { alive = false; };
  }, [engagementId, onLoad]);
  if (!progress) return null;
  return (
    <div className="mb-4 flex flex-wrap items-center gap-3 rounded-xl border border-border bg-card p-4 text-sm shadow-card" data-testid="checklist-status">
      <Badge variant="brand">{STAGE_LABEL[progress.stage]}</Badge>
      {progress.checklistSentAt ? (
        <span>Your auditor sent the checklist on {formatDate(progress.checklistSentAt)}. {progress.percentSubmitted}% of requests are with your auditor.</span>
      ) : (
        <span>Your auditor has not sent the checklist yet. You can look around; uploads open once it is sent.</span>
      )}
    </div>
  );
}
