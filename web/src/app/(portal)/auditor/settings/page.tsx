"use client";
import { useState } from "react";
import { AuthGate, useSession } from "@/components/auth/session";
import { PageHeader } from "@/components/shell/page";
import { Input } from "@/components/ui/input";
import { MFARecoveryCodes } from "@/components/auditor/mfa-recovery-codes";
import { Button } from "@/components/ui/button";

function Settings() {
  const { session } = useSession();
  const [saved, setSaved] = useState(false);
  return (
    <>
      <PageHeader
        title="Settings"
        description="Your profile, workspace preferences, and account security."
      />
      <div className="mb-6 rounded-lg border border-border bg-brand-tint p-4 text-sm text-brand">
        Preview settings · Profile, firm and notification edits are mock
        preferences for this page only.
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          setSaved(true);
        }}
        className="grid gap-[var(--space-6)] md:grid-cols-[11rem_minmax(0,1fr)]"
      >
        <nav
          aria-label="Settings sections"
          className="flex flex-wrap gap-[var(--space-2)] md:flex-col md:items-start"
        >
          {["Profile", "MFA", "Firm", "Notifications"].map((name) => (
            <a
              key={name}
              href={`#settings-${name.toLowerCase()}`}
              className="inline-flex min-h-[var(--control-height)] items-center rounded-[var(--control-radius)] px-[var(--space-3)] text-sm leading-snug text-muted hover:bg-elevated hover:text-foreground"
            >
              {name}
            </a>
          ))}
        </nav>
        <div className="grid max-w-3xl gap-5">
          {" "}
          <section
            id="settings-profile"
            className="scroll-mt-24 rounded-xl border border-border bg-surface p-6"
          >
            <h2 className="text-lg font-semibold">Profile</h2>
            <p className="mb-5 text-sm text-muted">
              How you appear in your workspace.
            </p>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="grid gap-2 text-sm">
                Display name
                <Input
                  defaultValue={session?.user.name ?? ""}
                  autoComplete="name"
                />
              </label>
              <label className="grid gap-2 text-sm">
                Email
                <Input
                  type="email"
                  defaultValue={session?.user.email ?? ""}
                  autoComplete="email"
                />
              </label>
            </div>
          </section>
          <section
            id="settings-mfa"
            className="scroll-mt-24 rounded-xl border border-border bg-surface p-6"
          >
            <h2 className="text-lg font-semibold">MFA</h2>
            <p className="mt-2 text-sm text-muted">
              Auditor access requires backend-enforced multi-factor
              authentication. Preview preferences do not change account
              security.
            </p>
            <p className="mt-4 rounded-md bg-elevated p-3 text-sm">
              Security preferences preview · MFA policy is managed by Kien Solutions.
            </p>
          </section>
          <section
            id="settings-firm"
            className="scroll-mt-24 rounded-xl border border-border bg-surface p-6"
          >
            <h2 className="mb-4 text-lg font-semibold">Firm</h2>
            <label className="grid gap-2 text-sm">
              Workspace name
              <Input defaultValue="Kien Operations" />
            </label>
            <p className="mt-3 text-xs text-muted">
              Workspace membership and engagement assignments are managed by
              your administrator.
            </p>
          </section>
          <section
            id="settings-notifications"
            className="scroll-mt-24 rounded-xl border border-border bg-surface p-6"
          >
            <h2 className="mb-2 text-lg font-semibold">Notifications</h2>
            <p className="mb-4 text-sm text-muted">
              Choose the updates you would like to receive. Preview only; no
              messages are sent.
            </p>
            {[
              "New document uploads",
              "Upcoming task reminders",
              "Weekly engagement digest",
            ].map((label) => (
              <label
                key={label}
                className="flex items-center justify-between gap-4 border-b border-border py-2 text-sm last:border-0"
              >
                {label}
                <input
                  type="checkbox"
                  defaultChecked
                  className="size-5 accent-brand"
                />
              </label>
            ))}
          </section>
          <div className="flex items-center gap-4">
            <Button type="submit">Save preview preferences</Button>
            {saved && (
              <p role="status" className="status-note" data-tone="success">
                Preview preferences saved for this page only.
              </p>
            )}
          </div>
        </div>
      </form>
      <div className="mt-6 max-w-3xl lg:ml-[204px]">
        <MFARecoveryCodes />
      </div>
    </>
  );
}
export default function SettingsPage() {
  return (
    <AuthGate role="auditor">
      <Settings />
    </AuthGate>
  );
}
