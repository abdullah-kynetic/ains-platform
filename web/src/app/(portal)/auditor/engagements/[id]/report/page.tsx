import { ReportTab } from "@/components/auditor/engagement/report-signoff";

export const metadata = { title: "Report" };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ReportTab id={id} />;
}
