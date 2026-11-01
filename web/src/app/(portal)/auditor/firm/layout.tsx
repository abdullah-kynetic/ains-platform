"use client";

import { AuthGate } from "@/components/auth/session";
import { LinkTabs } from "@/components/ui/tabs";

const tabs = [
  { href: "/auditor/firm/team", label: "Team and roles" },
  { href: "/auditor/firm/branding", label: "Branding" },
  { href: "/auditor/firm/rubric", label: "Rubric" },
  { href: "/auditor/firm/templates", label: "Request templates" },
];

export default function FirmLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGate role="auditor">
      <LinkTabs tabs={tabs} className="mb-4" />
      {children}
    </AuthGate>
  );
}
