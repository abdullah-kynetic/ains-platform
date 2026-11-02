import { WorkpapersTab } from "@/components/auditor/engagement/checklist-workpapers";

export const metadata = { title: "Workpapers" };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <WorkpapersTab id={id} />;
}
