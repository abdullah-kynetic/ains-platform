"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { PageHeader, Stat } from "@/components/shell/page";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { buttonVariants } from "@/components/ui/button";
import { getChecklistTests, getEngagementSummary, listActivity, listFindings, listSamples, sampleStats, signoffBlockers } from "@/lib/api/index";
import { sectionName } from "@/lib/mock/seed";
import { Loading, MockNotice, fmtDateTime, useAsync } from "../kit";
import { ClientChecklistCard } from "./client-flow";

export function Overview({ id }: { id: string }) {
  const { data, error, reload } = useAsync(async () => {
    const [summary, tests, findings, samples, blockers, activity] = await Promise.all([getEngagementSummary(id), getChecklistTests(id), listFindings(id), listSamples(id), signoffBlockers(id), listActivity(id)]);
    return { summary, tests, findings, samples, blockers, activity };
  }, [id]);
  if (!data) return <Loading error={error} retry={reload} label="Loading engagement…" />;
  const { summary, tests, findings, samples, blockers, activity } = data;
  const concluded = tests.filter((t) => t.conclusion !== null).length;
  const exceptions = samples.reduce((n, s) => n + sampleStats(s).exceptions, 0);
  const sections = [...new Set(tests.map((t) => t.section))].map((s) => {
    const rows = tests.filter((t) => t.section === s);
    return { id: s, done: rows.filter((r) => r.conclusion !== null).length, total: rows.length };
  });
  return (
    <>
      <PageHeader title="Overview" description={summary ? `${summary.firmName}: ${summary.period} Rule 3310 independent test.` : undefined}
        actions={<Link href={`/auditor/engagements/${id}/checklist`} className={buttonVariants({ variant: "outline" })}>Open checklist</Link>} />
      <ClientChecklistCard id={id} />
      <MockNotice />
      <div className="mb-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Checklist concluded" value={`${concluded} of ${tests.length}`} hint="Pass, partial, fail or does not apply" />
        <Stat label="Open findings" value={findings.filter((f) => f.status !== "closed").length} hint={`${findings.filter((f) => f.status === "draft").length} still draft`} />
        <Stat label="Sample exceptions" value={exceptions} hint={`${samples.length} sample sets`} />
        <Stat label="Sign-off blockers" value={blockers.length} hint={blockers.length ? "Resolve before review" : "Ready for second review"} />
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>Progress by section</CardTitle></CardHeader>
          <CardContent>
            <ul className="grid gap-3">
              {sections.map((s) => (
                <li key={s.id}>
                  <div className="mb-1 flex justify-between text-sm"><span>{sectionName(s.id)}</span><span className="text-muted tabular-nums">{s.done} of {s.total}</span></div>
                  <div role="img" aria-label={`${s.done} of ${s.total} concluded`} className="h-2 overflow-hidden rounded-full bg-elevated"><div className="h-full bg-foreground" style={{ width: `${(s.done / s.total) * 100}%` }} /></div>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Engagement team</CardTitle></CardHeader>
          <CardContent>
            <dl className="grid gap-3 text-sm">
              {[["Lead auditor", summary?.lead], ["Second reviewer", summary?.reviewer], ["Partner (signs)", summary?.partner]].map(([k, v]) => <div key={k}><dt className="text-muted">{k}</dt><dd className="font-medium">{v}</dd></div>)}
            </dl>
          </CardContent>
        </Card>
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>Before sign-off</CardTitle></CardHeader>
          <CardContent>
            {blockers.length === 0 ? <p className="text-sm text-muted">Nothing is blocking second review.</p> : (
              <ul className="grid gap-2 text-sm">{blockers.map((b) => <li key={b} className="flex gap-2"><span aria-hidden className="mt-2 size-1.5 shrink-0 rounded-full bg-warning" />{b}</li>)}</ul>
            )}
            <Link href={`/auditor/engagements/${id}/sign-off`} className="mt-4 inline-flex items-center gap-1 text-sm underline underline-offset-4">Go to sign-off <ArrowRight aria-hidden className="size-3.5" /></Link>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Recent activity</CardTitle></CardHeader>
          <CardContent>
            <ul className="divide-y divide-border text-sm">
              {activity.slice(0, 4).map((a) => <li key={a.id} className="py-2 first:pt-0"><p>{a.action}</p><p className="text-xs text-muted">{a.actor} · {fmtDateTime(a.at)}</p></li>)}
            </ul>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
