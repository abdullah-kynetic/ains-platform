import { SamplesTab } from "@/components/auditor/engagement/samples";

export const metadata = { title: "Samples" };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <SamplesTab id={id} />;
}
