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
  { href: "/auditor/pipeline", label: "Audit pipeline", icon: "Columns3" },
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

  async function handleWorkspaceChange(workspace: "auditor" | "client") {
    if (!USE_MOCKS || workspace === user?.role) return;
    localStorage.setItem("ains-synthetic-role", workspace);
    await refresh();
    router.push(workspace === "auditor" ? "/auditor" : "/");
  }

  return (
    <AuthGate>
      <Shell
        sidebar={
          <Sidebar
            items={isAuditor ? auditorItems : clientItems}
            sub={isAuditor ? "Auditor workspace" : "Client portal"}
            who={user?.name ?? user?.email ?? "Signed-in user"}
            org={
              isAuditor
                ? "AINS independent review"
                : "Example Securities LLC (synthetic)"
            }
            onSignOut={() => void handleSignOut()}
            onWorkspaceChange={
              USE_MOCKS
                ? (workspace) => void handleWorkspaceChange(workspace)
                : undefined
            }
          />
        }
      >
        {children}
      </Shell>
    </AuthGate>
  );
}
