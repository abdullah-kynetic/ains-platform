import { EngagementShell } from "@/components/auditor/engagement/shell";

export default async function EngagementLayout({ children, params }: { children: React.ReactNode; params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <EngagementShell id={id}>{children}</EngagementShell>;
}
