import { Shell } from "@/components/shell/page";
import { Sidebar, type NavItem } from "@/components/shell/nav";

const items: NavItem[] = [
  { href: "/", label: "Overview", icon: "LayoutDashboard", exact: true },
  { href: "/checklist", label: "Documents", icon: "Files" },
];

export default function PortalLayout({ children }: { children: React.ReactNode }) {
  // Auth is not wired yet: identity will come from the AINS API session.
  return <Shell sidebar={<Sidebar items={items} sub="Audit workspace" who="Quinton" org="Example Securities LLC (synthetic)" />}>{children}</Shell>;
}
