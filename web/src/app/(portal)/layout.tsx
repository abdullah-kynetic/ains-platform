"use client";

import { Shell } from "@/components/shell/page";
import { Sidebar, type NavItem } from "@/components/shell/nav";
import { AuthGate, useSession } from "@/components/auth/session";
import { useRouter } from "next/navigation";
import { USE_MOCKS } from "@/lib/api";

const clientItems: NavItem[] = [
  { href: "/", label: "Overview", icon: "LayoutDashboard", exact: true },
  { href: "/checklist", label: "Document checklist", icon: "ListChecks" },
  { href: "/upload", label: "Upload center", icon: "Upload" },
  { href: "/questionnaire", label: "Firm questionnaire", icon: "ClipboardCheck" },
];

const auditorItems: NavItem[] = [
  { href: "/auditor", label: "Review queue", icon: "ShieldCheck", exact: true },
];

export default function PortalLayout({ children }: { children: React.ReactNode }) {
  const { session, logOut } = useSession();
  const router = useRouter();
  const user = session?.user;
  const isAuditor = user?.role === "auditor";

  async function handleSignOut() {
    await logOut();
    router.replace("/sign-in");
  }

  return (
    <AuthGate>
      <Shell sidebar={
        <Sidebar
          items={isAuditor ? auditorItems : clientItems}
          sub={isAuditor ? "Auditor workspace" : "Client portal"}
          who={user?.name ?? user?.email ?? "Signed-in user"}
          org={isAuditor ? "AINS independent review" : undefined}
          onSignOut={() => void handleSignOut()}
        />
      }>
        {USE_MOCKS && <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border p-3 text-sm"><span>Synthetic demo — {isAuditor ? "auditor" : "client"} view. No real documents.</span><button className="underline" onClick={() => { localStorage.setItem("ains-synthetic-role", isAuditor ? "client" : "auditor"); window.location.assign(isAuditor ? "/" : "/auditor"); }}>Switch to {isAuditor ? "client" : "auditor"} demo</button></div>}
        {children}
      </Shell>
    </AuthGate>
  );
}
