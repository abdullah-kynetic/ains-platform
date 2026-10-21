"use client";

import { Shell } from "@/components/shell/page";
import { Sidebar, type NavItem } from "@/components/shell/nav";
import { AuthGate, useSession } from "@/components/auth/session";
import { useRouter } from "next/navigation";
import { USE_MOCKS, type UserRole } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { ThemeControl } from "@/components/shell/theme-control";

const clientItems: NavItem[] = [
  { href: "/", label: "Overview", icon: "LayoutDashboard", exact: true },
  { href: "/checklist", label: "Document checklist", icon: "ListChecks" },
  { href: "/progress", label: "Progress", icon: "ChartNoAxesCombined" },
  { href: "/questionnaire", label: "Firm questionnaire", icon: "ClipboardCheck" },
];

const auditorItems: NavItem[] = [
  { href: "/auditor", label: "Review queue", icon: "ShieldCheck", exact: true },
  { href: "/auditor/manage", label: "Engagement setup", icon: "Building2" },
];

export default function PortalLayout({ children }: { children: React.ReactNode }) {
  const { session, logOut, refresh } = useSession();
  const router = useRouter();
  const user = session?.user;
  const isAuditor = user?.role === "auditor";

  async function handleSignOut() {
    await logOut();
    router.replace("/sign-in");
  }

  async function switchDemo(role: UserRole) {
    sessionStorage.setItem("ains-demo-role", role);
    // Remove a direct-link role selector so it cannot override the selected view.
    window.history.replaceState(null, "", window.location.pathname);
    await refresh();
    router.replace(role === "auditor" ? "/auditor" : "/");
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
        <ThemeControl />
        {USE_MOCKS ? <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-brand/30 bg-surface p-4">
          <div><p className="text-sm font-semibold">Synthetic demo</p><p className="text-xs text-muted">No real accounts. Uploads and review decisions are simulated. Changes reset on refresh.</p></div>
          <div className="flex gap-2">
            <Button size="sm" variant={isAuditor ? "outline" : "default"} onClick={() => void switchDemo("client")}>Client view</Button>
            <Button size="sm" variant={isAuditor ? "default" : "outline"} onClick={() => void switchDemo("auditor")}>Auditor view</Button>
          </div>
        </div> : null}
        {children}
      </Shell>
    </AuthGate>
  );
}
