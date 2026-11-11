"use client";

import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { AuthGate } from "@/components/auth/session";
import { Badge } from "@/components/ui/badge";
import { LinkTabs } from "@/components/ui/tabs";
import { getEngagementSummary } from "@/lib/api/index";
import { fmtDate, useAsync } from "../kit";

const tabs = (id: string) => [
  { href: `/auditor/engagements/${id}`, label: "Overview", exact: true },
  { href: `/auditor/engagements/${id}/client-checklist`, label: "Client checklist" },
  { href: `/auditor/engagements/${id}/requests`, label: "Requests" },
  { href: `/auditor/engagements/${id}/documents`, label: "Documents" },
  { href: `/auditor/engagements/${id}/checklist`, label: "Checklist" },
  { href: `/auditor/engagements/${id}/workpapers`, label: "Workpapers" },
  { href: `/auditor/engagements/${id}/samples`, label: "Samples" },
  { href: `/auditor/engagements/${id}/findings`, label: "Findings" },
  { href: `/auditor/engagements/${id}/report`, label: "Report" },
  { href: `/auditor/engagements/${id}/independence`, label: "Independence" },
  { href: `/auditor/engagements/${id}/sign-off`, label: "Sign-off" },
  { href: `/auditor/engagements/${id}/activity`, label: "Activity" },
];

export function EngagementShell({ id, children }: { id: string; children: React.ReactNode }) {
  const { data } = useAsync(() => getEngagementSummary(id), [id]);
  return (
    <AuthGate role="auditor">
      <div className="mb-3 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted">
        <Link href="/auditor/engagements" className="hover:text-foreground">Engagements</Link>
        <ChevronRight aria-hidden className="size-3.5 text-subtle" />
        {data ? (
          <>
            <Link href={`/auditor/clients/${data.clientId}`} className="font-medium text-foreground hover:underline">{data.firmName}</Link>
            <span aria-hidden>·</span><span>{data.period}</span>
            <Badge variant="brand">{data.stage}</Badge>
            {data.due && <Badge variant="deadline">Due {fmtDate(data.due)}</Badge>}
          </>
        ) : <span>{id}</span>}
      </div>
      <LinkTabs tabs={tabs(id)} className="mb-4" />
      {children}
    </AuthGate>
  );
}
