"use client";
import { PageHeader } from "@/components/shell/page";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { ChecklistItemRow } from "@/components/checklist/checklist-item";
import { useEngagement } from "@/components/checklist/use-engagement";
import { progressOf } from "@/lib/checklist";
import Link from "next/link";

export default function ChecklistPage() {
  const { data, error } = useEngagement();
  if (error) return <p className="text-sm text-red-400">Couldn&apos;t load the checklist: {error}</p>;
  if (!data) return <Skeleton className="h-96 w-full" />;
  const p = progressOf(data);
  return (
    <>
      <PageHeader title="Document checklist" description="Review requests and track receipts. Receipt is not an audit conclusion." />
      <Link href="/upload" className="mb-5 inline-block rounded-lg bg-brand px-4 py-2 text-white">Go to upload center</Link>
      <div className="mb-5 grid gap-2">
        <Progress value={p.pct} />
        <p className="text-xs text-muted">{p.done} of {p.total} items received</p>
      </div>
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
                {s.items.map((i) => <ChecklistItemRow key={i.id} item={i} />)}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </>
  );
}
