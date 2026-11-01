import { DocumentsTab } from "@/components/auditor/engagement/documents-activity";

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <DocumentsTab id={id} />;
}
