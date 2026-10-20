import { AuditorWorkspace } from "@/components/auditor/workspace";

export default async function AuditorEngagementPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <AuditorWorkspace engagementId={id} />;
}
