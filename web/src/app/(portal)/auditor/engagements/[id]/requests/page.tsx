import { ManualWorkspace } from "@/components/auditor/manual-workspace";

export default async function RequestsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ManualWorkspace engagementId={id} />;
}
