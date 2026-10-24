"use client";

import Link from "next/link";
import { useEngagement } from "@/components/checklist/use-engagement";
import { StatusBadge } from "@/components/checklist/status-badge";
import { PageHeader, Stat } from "@/components/shell/page";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { LoadState } from "@/components/ui/load-state";
import { buttonVariants } from "@/components/ui/button";
import { countByStatus, progressOf } from "@/lib/checklist";

export default function ClientProgressPage() {
  const { data, error, reload } = useEngagement();
  if (error || !data) return <LoadState error={error} retry={reload} />;
  const progress = progressOf(data);
  const counts = countByStatus(data);
  return <>
    <PageHeader title="Your document progress" description="Track what has been received, what is being checked, and what needs your attention. Document acceptance is not an audit conclusion."
      actions={<Link href="/checklist" className={buttonVariants()}>Upload documents</Link>} />
    <div className="mb-5 grid gap-3 sm:grid-cols-3">
      <Stat label="Documents received" value={`${progress.done} / ${progress.total}`} />
      <Stat label="Being checked" value={counts.checking} />
      <Stat label="Needs your attention" value={counts.requested + counts.action_needed_more + counts.action_needed_reupload} />
    </div>
    <div className="grid gap-4">{data.sections.map((section) => {
      const p = progressOf({ ...data, sections: [section] });
      return <Card key={section.id}>
        <CardHeader><CardTitle>{section.title}</CardTitle></CardHeader>
        <CardContent className="grid gap-3">
          <Progress value={p.pct} label={`${section.title} document collection progress`} />
          <p className="text-xs text-muted">{p.done} of {p.total} uploadable requests received</p>
          {section.items.map((item) => <div key={item.id} className="flex flex-wrap items-center justify-between gap-2 border-b border-border py-2 text-sm">
            <span>{item.title}</span><StatusBadge status={item.status} />
          </div>)}
        </CardContent>
      </Card>;
    })}</div>
  </>;
}
