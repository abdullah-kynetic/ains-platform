import { SignoffTab } from "@/components/auditor/engagement/report-signoff";

export const metadata = { title: "Sign-off" };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <SignoffTab id={id} />;
}
