"use client";
import { PageHeader } from "@/components/shell/page";
import { LoadState } from "@/components/ui/load-state";
import { useEngagement } from "@/components/checklist/use-engagement";
import Link from "next/link";
export default function MessagesPage() {
  const { data, error, reload } = useEngagement();
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
        className="grid max-w-3xl gap-4"
      >
        {requests.length ? (
          requests.map((item) => (
            <article
              key={item.id}
              className="rounded-xl border border-border bg-surface p-6"
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
        ) : (
          <p className="rounded-xl border border-border bg-surface p-6 text-muted">
            No document follow-ups right now.
          </p>
        )}
      </section>
    </>
  );
}
