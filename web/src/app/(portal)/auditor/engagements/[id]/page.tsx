import { EngagementWorkspace } from "@/components/auditor/engagement-workspace";

export default async function AuditorEngagementPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <EngagementWorkspace engagementId={id} />;
}
