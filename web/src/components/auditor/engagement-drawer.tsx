"use client";

import { AuditTimeline } from "./audit-log";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Sheet } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { buttonVariants } from "@/components/ui/button";
import { getAuditorActivity, type AuditorActivity, type ClientSummary } from "@/lib/workflow-api";

export function EngagementDrawer({ client, onClose }: { client: ClientSummary | null; onClose: () => void }) {
  return <Sheet open={Boolean(client)} onOpenChange={(open) => { if (!open) onClose(); }} side="right" label="Engagement details" className="w-[520px] max-w-[100vw] bg-surface p-6 pt-16">
    {client && <RecordDetails key={client.id} client={client} />}
  </Sheet>;
}

function RecordDetails({ client }: { client: ClientSummary }) {
  const [activity, setActivity] = useState<AuditorActivity[] | null>(null);
  const [error, setError] = useState("");
  function load() {
    setError("");
    getAuditorActivity().then((items) => setActivity(items.filter((item) => item.engagementId === client.id))).catch(() => setError("Activity could not be loaded."));
  }
  useEffect(() => {
    let active = true;
    getAuditorActivity().then((items) => { if (active) setActivity(items.filter((item) => item.engagementId === client.id)); }).catch(() => { if (active) setError("Activity could not be loaded."); });
    return () => { active = false; };
  }, [client.id]);
  return <div className="grid gap-7">
    <div><Badge variant="brand">Assigned engagement</Badge><h2 className="mt-4 text-2xl font-semibold tracking-tight">{client.firmName}</h2><p className="mt-2 text-sm text-muted">Internal engagement record · Auditor access</p></div>
    <section className="rounded-xl border border-border bg-background p-5"><h3 className="font-semibold">Review progress</h3><p className="my-3 text-sm text-muted">{client.readiness.reviewed} of {client.readiness.total} requests reviewed</p><Progress value={client.readiness.total ? client.readiness.reviewed / client.readiness.total * 100 : 0} /><p className="mt-3 text-sm">{client.readiness.ready ? "Ready for report drafting" : "Review incomplete"}</p><p className="mt-2 text-xs text-muted">Findings and reports require an explicit auditor decision.</p></section>
    <section aria-labelledby="record-activity"><h3 id="record-activity" className="mb-5 font-semibold">Activity timeline</h3>
      {error ? <div role="alert"><p>{error}</p><button className="mt-2 text-brand underline" onClick={load}>Retry activity</button></div> : activity === null ? <p role="status">Loading activity…</p> : !activity.length ? <p className="text-sm text-muted">No activity recorded for this engagement.</p> : <ol className="ml-2 border-l border-border">{activity.map((item) => <li key={item.id} className="relative pb-6 pl-6"><span aria-hidden="true" className="absolute -left-1.5 top-1 size-3 rounded-full border-2 border-surface bg-brand" /><p className="text-sm"><span className="font-medium">{item.actor}</span> {item.action} {item.subject}</p><p className="mt-1 text-xs text-muted">{item.context}</p><time dateTime={item.occurredAt} className="mt-2 block text-xs text-subtle">{new Date(item.occurredAt).toLocaleString()}</time></li>)}</ol>}
    </section>
    <AuditTimeline firm={client.firmId ?? client.id} entityId={client.id} />
    <Link href={`/auditor/engagements/${client.id}`} className={buttonVariants()}>Continue to audit workspace</Link>
  </div>;
}
