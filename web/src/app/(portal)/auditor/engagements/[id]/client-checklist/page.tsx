import { ClientItemsPanel } from "@/components/auditor/engagement/client-flow";

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ClientItemsPanel id={id} />;
}
