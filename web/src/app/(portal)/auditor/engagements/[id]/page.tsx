import { Overview } from "@/components/auditor/engagement/overview";

export const metadata = { title: "Engagement overview" };

export default async function AuditorEngagementPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <Overview id={id} />;
}
