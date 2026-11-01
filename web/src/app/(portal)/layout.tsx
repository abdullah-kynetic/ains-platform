"use client";

import { Shell } from "@/components/shell/page";
import { Sidebar, type NavItem } from "@/components/shell/nav";
import { AuthGate, useSession } from "@/components/auth/session";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getEngagement } from "@/lib/api";
import { countByStatus } from "@/lib/checklist";
import { getAuditorTasks, getClients, getPipeline } from "@/lib/workflow-api";
import { Onboarding } from "@/components/auth/onboarding";
import { USE_MOCKS } from "@/lib/api";

const clientItems: NavItem[] = [
  { href: "/", label: "Overview", icon: "LayoutDashboard", exact: true, group: "Engagement" },
  { href: "/upload", label: "Upload", icon: "Upload", group: "Engagement" },
  { href: "/checklist", label: "Checklist", icon: "ListChecks", group: "Engagement" },
  { href: "/questionnaire", label: "Questionnaire", icon: "ClipboardCheck", group: "Engagement" },
  { href: "/messages", label: "Messages", icon: "MessagesSquare", group: "Updates" },
  { href: "/progress", label: "Progress", icon: "ChartNoAxesCombined", group: "Updates" },
];

const auditorItems: NavItem[] = [
  { href: "/auditor", label: "Today", icon: "LayoutDashboard", exact: true, group: "Workspace" },
  { href: "/auditor/engagements", label: "Engagements", icon: "Building2", group: "Workspace" },
  { href: "/auditor/pipeline", label: "Audit pipeline", icon: "Columns3", group: "Workspace" },
  { href: "/auditor/reports", label: "Reports", icon: "ClipboardCheck", group: "Deliverables" },
  { href: "/auditor/invoices", label: "Invoices", icon: "Receipt", group: "Deliverables" },
  { href: "/auditor/audit-log", label: "Audit Log", icon: "History", group: "Administration" },
  { href: "/auditor/settings", label: "Settings", icon: "Settings", group: "Administration" },
];

const today = () => new Date().toISOString().slice(0, 10);

/** Sidebar counts come only from endpoints the pages already call. */
function useNavCounts(isAuditor: boolean, enabled: boolean) {
  const [counts, setCounts] = useState<Record<string, number>>({});
  useEffect(() => {
    if (!enabled) return;
    let active = true;
    const load = isAuditor
      ? Promise.all([getClients(), getPipeline(), getAuditorTasks()]).then(
          ([clients, pipeline, tasks]) => ({
            "/auditor": tasks.filter((task) => !task.completed && task.due !== null && task.due <= today()).length,
            "/auditor/engagements": clients.length,
            "/auditor/pipeline": pipeline.filter((entry) => entry.stage !== "complete").length,
            "/auditor/reports": pipeline.filter((entry) => entry.stage === "report_drafting" || entry.stage === "awaiting_signature").length,
          }),
        )
      : getEngagement().then((engagement) => {
          const status = countByStatus(engagement);
          return {
            "/checklist": status.requested + status.action_needed_reupload + status.action_needed_more,
            "/messages": status.action_needed_reupload + status.action_needed_more,
          };
        });
    load.then((value) => { if (active) setCounts(value); }).catch(() => { if (active) setCounts({}); });
    return () => { active = false; };
  }, [isAuditor, enabled]);
  return counts;
}

export default function PortalLayout({ children }: { children: React.ReactNode }) {
  const { session, logOut, refresh } = useSession();
  const router = useRouter();
  const user = session?.user;
  const isAuditor = user?.role === "auditor";
  const counts = useNavCounts(isAuditor, Boolean(user));
  const items = (isAuditor ? auditorItems : clientItems).map((item) =>
    !counts[item.href] ? item : { ...item, count: counts[item.href] },
  );

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
      <Onboarding key={user?.id} />
      <Shell
        items={items}
        auditor={isAuditor}
        sidebar={
          <Sidebar
            items={items}
            sub={isAuditor ? "Auditor workspace" : "Client portal"}
            who={user?.name ?? user?.email ?? "Signed-in user"}
            org={
              isAuditor
                ? "Kien Solutions independent review"
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
