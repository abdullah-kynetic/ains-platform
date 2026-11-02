import { IndependenceTab } from "@/components/auditor/engagement/report-signoff";

export const metadata = { title: "Independence" };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <IndependenceTab id={id} />;
}
