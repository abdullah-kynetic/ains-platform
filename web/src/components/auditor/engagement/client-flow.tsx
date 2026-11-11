"use client";

import { useState } from "react";
import { Send } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress as Bar } from "@/components/ui/progress";
import { getProgress, sendChecklist, STAGE_LABEL } from "@/lib/api/flow";
import { fmtDateTime, useAsync } from "../kit";

/** Step 2: send the numbered checklist to the client and watch collection progress. */
export function ClientChecklistCard({ id }: { id: string }) {
  const { data, error, reload } = useAsync(() => getProgress(id, "auditor"), [id]);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState("");

  async function send() {
    setBusy(true);
    setFailure("");
    try {
      await sendChecklist(id);
      reload();
    } catch (caught) {
      setFailure(caught instanceof Error ? caught.message : "Could not send the checklist.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="mb-4" data-testid="client-checklist-card">
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle>Client checklist</CardTitle>
          <CardDescription>
            {data?.checklistSentAt
              ? `Sent ${fmtDateTime(data.checklistSentAt)}. The client sees the numbered requests 1 to ${data.items.length}.`
              : "The client cannot start until you send the numbered checklist."}
          </CardDescription>
        </div>
        <div className="flex items-center gap-2">
          {data ? <Badge variant="brand" data-testid="workflow-stage">{STAGE_LABEL[data.stage]}</Badge> : null}
          {data && !data.checklistSentAt ? (
            <Button onClick={() => void send()} disabled={busy}>
              <Send aria-hidden className="size-4" /> {busy ? "Sending…" : "Send checklist to client"}
            </Button>
          ) : null}
        </div>
      </CardHeader>
      <CardContent>
        {error ? <p role="alert" className="status-note" data-tone="danger">{error}</p> : null}
        {failure ? <p role="alert" className="status-note" data-tone="danger">{failure}</p> : null}
        {data ? (
          <div className="grid gap-2 text-sm">
            <div className="flex flex-wrap justify-between gap-2 text-muted">
              <span>{data.percentSubmitted}% submitted · {data.percentAccepted}% accepted for testing</span>
              <span className="tabular-nums">
                {data.counts.notStarted} not started · {data.counts.submitted} with you · {data.counts.needsInfo} need information · {data.counts.notApplicable} N/A
                {data.counts.naPending ? ` · ${data.counts.naPending} N/A requests to decide` : ""}
              </span>
            </div>
            <Bar value={data.percentSubmitted} />
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
