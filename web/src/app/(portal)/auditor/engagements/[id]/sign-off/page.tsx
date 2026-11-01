import { SignoffTab } from "@/components/auditor/engagement/report-signoff";

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <SignoffTab id={id} />;
}
