import { ClientProfileView } from "@/components/auditor/clients";

export const metadata = { title: "Client profile" };
export default async function ClientPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ClientProfileView id={id} />;
}
