"use client";

import { Shell } from "@/components/shell/page";
import { Sidebar, type NavItem } from "@/components/shell/nav";
import { AuthGate, useSession } from "@/components/auth/session";
import { useRouter } from "next/navigation";

const clientItems: NavItem[] = [
  { href: "/", label: "Overview", icon: "LayoutDashboard", exact: true },
  { href: "/checklist", label: "Document checklist", icon: "ListChecks" },
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
        {children}
      </Shell>
    </AuthGate>
  );
}
