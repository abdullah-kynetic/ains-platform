import { ClientProfileView } from "@/components/auditor/clients";
export default async function ClientPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ClientProfileView id={id} />;
}
