"use client";

import { Shell } from "@/components/shell/page";
import { Sidebar, type NavItem } from "@/components/shell/nav";
import { AuthGate, useSession } from "@/components/auth/session";
import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { getEngagement } from "@/lib/api";
import { countByStatus } from "@/lib/checklist";
import { getAuditorTasks, getPipeline } from "@/lib/workflow-api";
import { listClientProfiles, listEngagementSummaries, listNotifications, unreadCount } from "@/lib/api/index";
import { currentAudience } from "@/lib/audience";
import { Onboarding } from "@/components/auth/onboarding";
import { USE_MOCKS } from "@/lib/api";
import { useTenant } from "@/components/tenant/tenant-provider";

const clientItems: NavItem[] = [
  { href: "/", label: "Overview", icon: "LayoutDashboard", exact: true, group: "Engagement" },
  { href: "/upload", label: "Upload", icon: "Upload", group: "Engagement" },
  { href: "/checklist", label: "Checklist", icon: "ListChecks", group: "Engagement" },
  { href: "/questionnaire", label: "Questionnaire", icon: "ClipboardCheck", group: "Engagement" },
  { href: "/messages", label: "Messages", icon: "MessagesSquare", group: "Updates" },
  { href: "/progress", label: "Progress", icon: "ChartNoAxesCombined", group: "Updates" },
  { href: "/responses", label: "Responses requested", icon: "MessageSquareReply", group: "Results" },
  { href: "/report", label: "Report", icon: "FileText", group: "Results" },
  { href: "/invoices", label: "Invoices", icon: "Receipt", group: "Results" },
];

const auditorItems: NavItem[] = [
  { href: "/auditor", label: "Today", icon: "LayoutDashboard", exact: true, group: "Workspace" },
  { href: "/auditor/clients", label: "Clients", icon: "Users", group: "Workspace" },
  { href: "/auditor/notifications", label: "Notifications", icon: "Bell", group: "Workspace" },
  { href: "/auditor/engagements", label: "Engagements", icon: "Building2", group: "Engagements" },
  { href: "/auditor/pipeline", label: "Audit pipeline", icon: "Columns3", group: "Engagements" },
  { href: "/auditor/reports", label: "Reports", icon: "ClipboardCheck", group: "Engagements" },
  { href: "/auditor/invoices", label: "Invoices", icon: "Receipt", group: "Engagements" },
  { href: "/auditor/firm", label: "Firm settings", icon: "Landmark", group: "Firm" },
  { href: "/auditor/audit-log", label: "Audit Log", icon: "History", group: "Firm" },
  { href: "/auditor/isolation", label: "Isolation proof", icon: "ShieldCheck", group: "Firm" },
  { href: "/auditor/settings", label: "My account", icon: "Settings", group: "Firm" },
];

const today = () => new Date().toISOString().slice(0, 10);

/** Sidebar counts come only from endpoints the pages already call. */
function useNavCounts(isAuditor: boolean, enabled: boolean) {
  const [counts, setCounts] = useState<Record<string, number>>({});
  useEffect(() => {
    if (!enabled) return;
    let active = true;
    const load = isAuditor
      ? Promise.all([listEngagementSummaries(), getPipeline(), getAuditorTasks(), listClientProfiles(), listNotifications()]).then(
          ([clients, pipeline, tasks, profiles, notifications]) => ({
            "/auditor/clients": profiles.length,
            "/auditor/notifications": unreadCount(notifications),
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
  const { branding } = useTenant();
  const router = useRouter();
  const pathname = usePathname();
  const user = session?.user;
  const isAuditor = user?.role === "auditor";
  // "/" is the client overview; auditors start on Today.
  useEffect(() => {
    if (isAuditor && pathname === "/") router.replace("/auditor");
  }, [isAuditor, pathname, router]);
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
                : USE_MOCKS
                  ? "Example Securities LLC (synthetic)"
                  : branding.name
            }
            onSignOut={() => void handleSignOut()}
            onWorkspaceChange={
              USE_MOCKS && currentAudience() === "both"
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
