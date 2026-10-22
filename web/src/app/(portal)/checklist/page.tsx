"use client";
import { PageHeader } from "@/components/shell/page";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { ChecklistItemRow } from "@/components/checklist/checklist-item";
import { useEngagement } from "@/components/checklist/use-engagement";
import { progressOf } from "@/lib/checklist";

export default function ChecklistPage() {
  const { data, error, upload } = useEngagement();
  if (error) return <p className="text-sm text-danger-foreground">Couldn&apos;t load the checklist: {error}</p>;
  if (!data) return <Skeleton className="h-96 w-full" />;
  const p = progressOf(data);
  return (
    <>
      <PageHeader title="Documents" description="Upload each requested document. We check every file and tell you if anything needs fixing." />
      <Card className="mb-5">
        <CardContent className="grid gap-3 pt-5">
          <div className="flex items-center justify-between gap-3"><span className="text-xs font-medium text-muted">Overall readiness</span><span className="text-xs font-semibold tabular-nums">{Math.round(p.pct)}%</span></div>
          <Progress value={p.pct} />
          <p className="text-[11px] text-subtle">{p.done} of {p.total} items received</p>
        </CardContent>
      </Card>
      <div className="grid gap-5">
        {data.sections.map((s) => {
          const sp = progressOf({ ...data, sections: [s] });
          return (
            <Card key={s.id}>
              <CardHeader>
                <div className="flex items-center justify-between gap-3">
                  <CardTitle>{s.title}</CardTitle>
                  <span className="text-xs text-muted">{sp.done}/{sp.total}</span>
                </div>
                {s.description ? <CardDescription>{s.description}</CardDescription> : null}
              </CardHeader>
              <CardContent>
                {s.items.map((i) => <ChecklistItemRow key={i.id} item={i} onUpload={upload} />)}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </>
  );
}
