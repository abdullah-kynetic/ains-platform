import { InvoiceDetail } from "@/components/auditor/invoices";

export const metadata = { title: "Invoice" };
export default async function Page({ params }: { params: Promise<{ id: string }> }) { const { id } = await params; return <InvoiceDetail id={id} />; }
