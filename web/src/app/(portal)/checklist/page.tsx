"use client";

import Link from "next/link";
import { ChecklistStatus } from "@/components/portal/checklist-status";
import { RequestList } from "@/components/portal/request-list";
import { PageHeader } from "@/components/shell/page";
import { LoadState } from "@/components/ui/load-state";
import { buttonVariants } from "@/components/ui/button";
import { useEngagement } from "@/components/checklist/use-engagement";

export default function ChecklistPage() {
  const { data, error, reload } = useEngagement();
  if (error || !data) return <LoadState error={error} retry={reload} />;
  return (
    <>
      <PageHeader
        title="Document checklist"
        description="Your numbered document requests. A file receipt is not an audit conclusion."
        actions={
          <Link href="/upload" className={buttonVariants()}>
            Go to upload center
          </Link>
        }
      />
      <ChecklistStatus engagementId={data.id} />
      <RequestList engagementId={data.id} />
    </>
  );
}
