import { DocumentsTab } from "@/components/auditor/engagement/documents-activity";

export const metadata = { title: "Documents" };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <DocumentsTab id={id} />;
}
