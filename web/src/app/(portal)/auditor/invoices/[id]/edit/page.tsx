import { InvoiceForm } from "@/components/auditor/invoices";

export const metadata = { title: "Edit invoice" };
export default async function Page({ params }: { params: Promise<{ id: string }> }) { const { id } = await params; return <InvoiceForm id={id} />; }
