import { FindingsTab } from "@/components/auditor/engagement/findings";

export const metadata = { title: "Findings" };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <FindingsTab id={id} />;
}
