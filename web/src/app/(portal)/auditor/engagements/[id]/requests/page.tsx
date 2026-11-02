import { ManualWorkspace } from "@/components/auditor/manual-workspace";

export const metadata = { title: "Requests" };

export default async function RequestsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ManualWorkspace engagementId={id} />;
}
