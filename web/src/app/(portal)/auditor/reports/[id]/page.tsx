import { ReportEditor } from "@/components/auditor/reports";

export const metadata = { title: "Report" };
export default async function Page({params}:{params:Promise<{id:string}>}){const {id}=await params;return <ReportEditor id={id} />;}
