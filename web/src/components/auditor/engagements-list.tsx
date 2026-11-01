"use client";

import Link from "next/link";
import { useState } from "react";
import { Building2, Plus } from "lucide-react";
import { AuthGate } from "@/components/auth/session";
import { PageHeader } from "@/components/shell/page";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Select } from "@/components/ui/select";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { listEngagementSummaries } from "@/lib/api/index";
import { getPipeline } from "@/lib/workflow-api";
import { Loading, MockNotice, fmtDate, useAsync } from "./kit";

export function EngagementsList() {
  const { data, error, reload } = useAsync(async () => {
    const [summaries, pipeline] = await Promise.all([listEngagementSummaries(), getPipeline()]);
    return summaries.map((s) => ({ ...s, pipeline: pipeline.find((p) => p.id === s.id) }));
  }, []);
  const [query, setQuery] = useState("");
  const [stage, setStage] = useState("all");
  const stages = [...new Set((data ?? []).map((e) => e.stage))];
  const rows = (data ?? []).filter((e) => (stage === "all" || e.stage === stage) && e.firmName.toLowerCase().includes(query.toLowerCase()));
  return (
    <AuthGate role="auditor">
      <PageHeader title="Engagements" description="Every Rule 3310 test you are assigned to, with stage, progress and due date."
        actions={<Link href="/auditor/workspaces/new" className={buttonVariants()}><Plus aria-hidden />New client workspace</Link>} />
      <MockNotice />
      {!data ? <Loading error={error} retry={reload} label="Loading engagements…" /> : (
        <>
          <div className="mb-4 flex flex-wrap gap-2">
            <Input aria-label="Search engagements" placeholder="Search engagements" className="w-full sm:w-64" value={query} onChange={(e) => setQuery(e.target.value)} />
            <div className="w-full sm:w-56"><Select aria-label="Filter by stage" value={stage} onChange={(e) => setStage(e.target.value)}><option value="all">All stages</option>{stages.map((s) => <option key={s}>{s}</option>)}</Select></div>
          </div>
          {rows.length === 0 ? <EmptyState icon={Building2} title="No engagements match" description="Change the search or stage filter." /> : (
            <Table>
              <caption className="sr-only">Engagements</caption>
              <THead><TR><TH>Client</TH><TH>Period</TH><TH>Stage</TH><TH>Progress</TH><TH>Due</TH><TH>Lead</TH></TR></THead>
              <TBody>
                {rows.map((e) => (
                  <TR key={e.id}>
                    <TD><Link href={`/auditor/engagements/${e.id}`} className="inline-flex items-center gap-2 font-medium underline-offset-4 hover:underline"><Building2 aria-hidden className="size-4 text-muted" />{e.firmName}</Link></TD>
                    <TD>{e.period}</TD>
                    <TD><Badge variant={e.stage === "Complete" ? "success" : "brand"}>{e.stage}</Badge></TD>
                    <TD className="min-w-32"><span className="mb-1 block text-xs tabular-nums text-muted">{e.pipeline?.progress ?? 0}%</span><Progress value={e.pipeline?.progress ?? 0} /></TD>
                    <TD>{e.due ? <Badge variant={e.stage === "Complete" ? "default" : "deadline"}>{fmtDate(e.due)}</Badge> : "—"}</TD>
                    <TD>{e.lead}</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          )}
        </>
      )}
    </AuthGate>
  );
}
