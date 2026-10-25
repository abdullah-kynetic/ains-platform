"use client";

import { useState } from "react";
import Link from "next/link";
import { ListChecks } from "lucide-react";
import { PageHeader } from "@/components/shell/page";
import { Progress } from "@/components/ui/progress";
import { LoadState } from "@/components/ui/load-state";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { buttonVariants } from "@/components/ui/button";
import { ChecklistItemRow } from "@/components/checklist/checklist-item";
import { useEngagement } from "@/components/checklist/use-engagement";
import { progressOf } from "@/lib/checklist";

export default function ChecklistPage() {
  const { data, error, reload } = useEngagement();
  const [search, setSearch] = useState("");

  if (error || !data) return <LoadState error={error} retry={reload} />;

  const progress = progressOf(data);
  const sections = data.sections
    .map((section) => ({
      ...section,
      items: section.items.filter((item) =>
        `${item.requestId} ${item.title}`
          .toLowerCase()
          .includes(search.toLowerCase()),
      ),
    }))
    .filter((section) => section.items.length);

  return (
    <>
      <PageHeader
        title="Document checklist"
        description="Your applicable requests, grouped into manageable sections. A file receipt is not an audit conclusion."
        actions={
          <Link href="/upload" className={buttonVariants()}>
            Go to upload center
          </Link>
        }
      />

      <div className="mb-[var(--space-6)] grid gap-[var(--space-3)] rounded-card border border-border bg-surface p-[var(--space-5)] shadow-card">
        <div className="flex flex-wrap justify-between gap-2 text-sm">
          <span className="font-medium">Document collection</span>
          <span className="text-muted">
            {progress.done} of {progress.total} requests have receipts
          </span>
        </div>
        <Progress value={progress.pct} />
      </div>

      <label className="mb-5 grid max-w-xl gap-2 text-sm font-medium">
        Search document requests
        <Input
          placeholder="Request ID or title"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
      </label>

      {!sections.length ? (
        <EmptyState
          icon={ListChecks}
          title={
            search ? "No matching requests" : "No active document requests"
          }
          description={
            search
              ? "Try a different request number or title."
              : "Your auditor will let you know when anything is needed. You can review your questionnaire answers at any time."
          }
          action={
            <Link href="/questionnaire" className="underline">
              Review questionnaire
            </Link>
          }
        />
      ) : null}

      <div className="grid gap-4">
        {sections.map((section) => (
          <details
            open
            key={section.id}
            className="rounded-card border border-border bg-surface p-[var(--space-5)] shadow-card"
          >
            <summary className="cursor-pointer text-base font-semibold">
              {section.title}
              <span className="ml-3 text-xs font-normal text-muted">
                {section.items.length} request
                {section.items.length === 1 ? "" : "s"}
              </span>
            </summary>
            <div className="mt-3">
              {section.items.map((item) => (
                <ChecklistItemRow key={item.id} item={item} />
              ))}
            </div>
          </details>
        ))}
      </div>
    </>
  );
}
