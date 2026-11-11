"use client";
import { MessageSquare } from "lucide-react";
import Link from "next/link";
import { PageHeader } from "@/components/shell/page";
import { LoadState } from "@/components/ui/load-state";
import { EmptyState } from "@/components/ui/empty-state";
import { useEngagement } from "@/components/checklist/use-engagement";
import { IssueThread } from "@/components/auditor/engagement/issue-threads";
import { getProgress, listIssues, type Issue, type Progress } from "@/lib/api/flow";
import { useCallback, useEffect, useState } from "react";
export default function MessagesPage() {
  const { data, error, reload } = useEngagement();
  const [threads, setThreads] = useState<{ issues: Issue[]; progress: Progress } | null>(null);
  const engagementId = data?.id;
  const loadThreads = useCallback(() => {
    if (!engagementId) return;
    Promise.all([listIssues(engagementId, "client"), getProgress(engagementId, "client")])
      .then(([issues, progress]) => setThreads({ issues, progress }))
      .catch(() => setThreads(null));
  }, [engagementId]);
  useEffect(loadThreads, [loadThreads]);
  if (!data || error) return <LoadState error={error} retry={reload} />;
  const requests = data.sections
    .flatMap((s) => s.items)
    .filter((i) => i.status.startsWith("action_needed"));
  return (
    <>
      <PageHeader
        title="Messages"
        description="Document follow-ups for your current engagement."
      />
      <section
        aria-label="Document follow-ups"
        className="grid max-w-3xl gap-[var(--space-4)]"
      >
        {threads?.issues.map((issue) => {
          const item = threads.progress.items.find((i) => i.id === issue.itemId);
          return <IssueThread key={issue.id} engagementId={data.id} issue={issue} role="client" label={item ? `${item.number}. ${item.requestId} ${item.title}` : "Document request"} onDone={loadThreads} />;
        })}
        {requests.length ? (
          requests.map((item) => (
            <article
              key={item.id}
              className="rounded-xl bg-card border border-border shadow-card p-4"
            >
              <p className="text-xs text-muted">Document request · {item.id}</p>
              <h2 className="mt-2 font-semibold">{item.title}</h2>
              <p className="mt-2 text-sm text-muted">
                A document needs your attention. Open the request to see the
                intake instructions.
              </p>
              <Link
                href="/checklist"
                className="mt-4 inline-block text-sm text-brand underline"
              >
                View document requests
              </Link>
            </article>
          ))
        ) : threads?.issues.length ? null : (
          <EmptyState
            icon={MessageSquare}
            title="No document follow-ups right now."
            description="When a document needs your attention, it will show up here."
          />
        )}
      </section>
    </>
  );
}
