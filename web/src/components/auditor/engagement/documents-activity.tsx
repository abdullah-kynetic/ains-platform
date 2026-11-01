"use client";

import { FileText, History } from "lucide-react";
import { PageHeader } from "@/components/shell/page";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { listActivity, listDocuments } from "@/lib/api/index";
import { Loading, MockNotice, fmtDate, fmtDateTime, useAsync } from "../kit";

export function DocumentsTab({ id }: { id: string }) {
  const { data, error, reload } = useAsync(() => listDocuments(id), [id]);
  return (
    <>
      <PageHeader title="Documents" description="Everything the client uploaded, with the SHA-256 recorded at upload. Feedback here is about the document only." />
      <MockNotice />
      {!data ? <Loading error={error} retry={reload} label="Loading documents…" /> : data.length === 0 ? (
        <EmptyState icon={FileText} title="No documents yet" description="Uploads appear here as the client sends them." />
      ) : (
        <Table>
          <THead><TR><TH>Document</TH><TH>Request</TH><TH>Pages</TH><TH>Uploaded</TH><TH>SHA-256</TH><TH>Document check</TH></TR></THead>
          <TBody>
            {data.map((d) => (
              <TR key={d.id}>
                <TD className="font-medium">{d.name}</TD><TD>{d.requestId}</TD><TD className="tabular-nums">{d.pages}</TD>
                <TD>{fmtDate(d.uploadedAt)}<div className="text-xs text-muted">{d.uploadedBy}</div></TD>
                <TD><code className="text-xs">{d.sha256.slice(0, 12)}…</code></TD>
                <TD>{d.feedback ? <Badge variant="warning" title={d.feedback}>Feedback sent</Badge> : <Badge variant="success">Usable</Badge>}{d.feedback && <p className="mt-1 max-w-64 text-xs text-muted">{d.feedback}</p>}</TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}
    </>
  );
}

export function ActivityTab({ id }: { id: string }) {
  const { data, error, reload } = useAsync(() => listActivity(id), [id]);
  return (
    <>
      <PageHeader title="Activity log" description="Every change on this engagement, newest first." />
      <MockNotice />
      {!data ? <Loading error={error} retry={reload} label="Loading activity…" /> : data.length === 0 ? (
        <EmptyState icon={History} title="No activity yet" description="Actions on this engagement are recorded here." />
      ) : (
        <ol className="divide-y divide-border rounded-xl border border-border bg-surface">
          {data.map((a) => (
            <li key={a.id} className="flex flex-wrap items-baseline justify-between gap-2 px-4 py-3 text-sm">
              <span>{a.action}</span><span className="text-xs text-muted">{a.actor} · {fmtDateTime(a.at)}</span>
            </li>
          ))}
        </ol>
      )}
    </>
  );
}
