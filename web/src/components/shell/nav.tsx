"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  Check,
  ChevronsUpDown,
  LogOut,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import * as Icons from "lucide-react";
import { Logo } from "@/components/brand/logo";
import { ThemeToggle } from "@/components/shell/theme-toggle";
import { Sheet } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

export type NavItem = {
  href: string;
  label: string;
  icon: keyof typeof Icons;
  exact?: boolean;
};

type Workspace = {
  name: string;
  type: string;
  mark: string;
  role: "auditor" | "client";
};

const workspaces: Workspace[] = [
  {
    name: "AINS Operations",
    type: "Internal workspace",
    mark: "AI",
    role: "auditor",
  },
  {
    name: "Example Securities LLC",
    type: "Client workspace · Synthetic",
    mark: "ES",
    role: "client",
  },
];

function WorkspaceSwitcher({
  auditor,
  onWorkspaceChange,
  onNavigate,
}: {
  auditor: boolean;
  onWorkspaceChange?: (workspace: "auditor" | "client") => void;
  onNavigate?: () => void;
}) {
  const [open, setOpen] = useState(false);
  const active = workspaces[auditor ? 0 : 1];

  return (
    <div className="relative">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className="flex min-h-[var(--control-height)] w-full items-center gap-[var(--space-3)] rounded-lg border border-border bg-surface p-[var(--space-2)] text-left shadow-card transition-colors hover:bg-hover"
      >
        <span className="grid size-8 shrink-0 place-items-center rounded-md bg-foreground text-xs font-semibold tracking-wide text-background">
          {active.mark}
        </span>
        <span className="min-w-0 flex-1">
          <span
            title={active.name}
            className="block break-words text-sm font-semibold text-foreground"
          >
            {active.name}
          </span>
        </span>
        <ChevronsUpDown className="size-3.5 text-subtle" />
      </button>

      {open ? (
        <div className="absolute inset-x-0 top-[calc(100%+8px)] z-50 rounded-lg border border-border bg-surface p-1.5 shadow-pop">
          <p className="px-2 py-1.5 text-xs font-semibold uppercase tracking-[0.12em] text-subtle">
            Workspaces
          </p>
          {workspaces.map((workspace) => {
            const current = active.name === workspace.name;
            const available = current || Boolean(onWorkspaceChange);
            return (
              <button
                key={workspace.name}
                type="button"
                disabled={!available}
                title={
                  available
                    ? undefined
                    : "This workspace is not available to the signed-in user"
                }
                onClick={() => {
                  setOpen(false);
                  onNavigate?.();
                  if (!current) onWorkspaceChange?.(workspace.role);
                }}
                className="flex w-full items-center gap-2.5 rounded-md px-2 py-2 text-left hover:bg-hover disabled:cursor-not-allowed disabled:opacity-55"
              >
                <span className="grid size-7 place-items-center rounded-md border border-border bg-elevated text-xs font-semibold">
                  {workspace.mark}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-xs font-medium">
                    {workspace.name}
                  </span>
                  <span className="block truncate text-xs text-subtle">
                    {workspace.type}
                  </span>
                </span>
                {current ? (
                  <Check className="size-3.5 text-brand" />
                ) : !available ? (
                  <span className="text-xs font-medium uppercase tracking-wide text-subtle">
                    Restricted
                  </span>
                ) : null}
              </button>
            );
          })}
          <Link
            href={auditor ? "/auditor/workspaces/new" : "#"}
            aria-disabled={!auditor}
            onClick={(event) => {
              if (!auditor) event.preventDefault();
              else onNavigate?.();
              setOpen(false);
            }}
            className="mt-1 flex w-full items-center gap-2.5 border-t border-border px-2 pt-2.5 pb-1 text-xs text-subtle hover:text-foreground aria-disabled:cursor-not-allowed aria-disabled:opacity-55"
          >
            <span className="grid size-7 place-items-center rounded-md border border-dashed border-border-strong">
              <Plus className="size-3.5" />
            </span>
            Add client workspace
          </Link>
        </div>
      ) : null}
    </div>
  );
}

function Items({
  items,
  onNavigate,
}: {
  items: NavItem[];
  onNavigate?: () => void;
}) {
  const pathname = usePathname();

  return (
    <nav aria-label="Main navigation" className="grid gap-1">
      {items.map((item) => {
        const Icon = Icons[item.icon] as LucideIcon;
        const active = item.exact
          ? pathname === item.href
          : pathname === item.href || pathname.startsWith(`${item.href}/`);

        return (
          <Link
            key={item.href}
            href={item.href}
            title={item.label}
            aria-label={item.label}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex min-h-[var(--control-height)] items-center gap-[var(--space-2)] rounded-md px-[var(--space-3)] py-[var(--space-2)] text-sm font-medium leading-snug transition-colors",
              active
                ? "bg-brand-tint text-brand"
                : "text-muted hover:bg-hover hover:text-foreground",
            )}
          >
            <Icon
              className={cn("size-4", active ? "text-brand" : "text-subtle")}
            />
            <span className="nav-label">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function Panel({
  items,
  sub,
  who,
  org,
  onNavigate,
  onSignOut,
  onWorkspaceChange,
  desktop = false,
}: {
  desktop?: boolean;
  items: NavItem[];
  sub: string;
  who: string;
  org?: string;
  onNavigate?: () => void;
  onSignOut?: () => void;
  onWorkspaceChange?: (workspace: "auditor" | "client") => void;
}) {
  const auditor = sub.toLowerCase().includes("auditor");

  return (
    <div className="sidebar-panel flex min-h-0 flex-1 flex-col overflow-y-auto p-3">
      {!desktop ? <Logo sub={sub} className="px-2 pt-2 pb-5" /> : null}
      <WorkspaceSwitcher
        auditor={auditor}
        onWorkspaceChange={onWorkspaceChange}
        onNavigate={onNavigate}
      />
      <p className="mt-7 mb-2 px-2.5 text-xs font-semibold uppercase tracking-[0.13em] text-subtle">
        {auditor ? "Review" : "Engagement"}
      </p>
      <Items items={items} onNavigate={onNavigate} />
      <div className="mt-auto flex items-center gap-2 border-t border-border px-1 pt-3">
        <span className="grid size-8 shrink-0 place-items-center rounded-full bg-elevated text-xs font-semibold text-muted">
          {initials(who)}
        </span>
        <div className="min-w-0 flex-1">
          <div
            title={who}
            className="truncate text-xs font-medium text-foreground"
          >
            {who}
          </div>
          <div title={org} className="truncate text-xs text-subtle">
            {org}
          </div>
        </div>
        <span title="Workspace access enforced" className="shrink-0">
          <ShieldCheck
            aria-hidden="true"
            className="size-3.5 text-success-foreground"
          />
          <span className="sr-only">Workspace access enforced</span>
        </span>
        <button
          type="button"
          aria-label="Sign out"
          title="Sign out"
          onClick={onSignOut}
          disabled={!onSignOut}
          className="grid size-8 shrink-0 place-items-center rounded-md text-subtle hover:bg-hover hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand disabled:opacity-60"
        >
          <LogOut aria-hidden="true" className="size-3.5" />
        </button>
      </div>
    </div>
  );
}

export function Sidebar(props: {
  items: NavItem[];
  sub: string;
  who: string;
  org?: string;
  onSignOut?: () => void;
  onWorkspaceChange?: (workspace: "auditor" | "client") => void;
}) {
  const [open, setOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  return (
    <>
      <aside
        data-collapsed={collapsed}
        className="desktop-sidebar sticky top-0 hidden h-screen w-64 shrink-0 border-r border-border bg-sidebar lg:flex lg:flex-col"
      >
        <div className="flex items-center justify-between gap-1 p-3">
          {!collapsed ? <Logo sub={props.sub} className="min-w-0" /> : null}
          <button
            type="button"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-expanded={!collapsed}
            onClick={() => setCollapsed(!collapsed)}
            className="grid size-8 shrink-0 place-items-center rounded-md text-muted hover:bg-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
          >
            {collapsed ? (
              <PanelLeftOpen className="size-4" />
            ) : (
              <PanelLeftClose className="size-4" />
            )}
          </button>
        </div>
        <Panel {...props} desktop />
      </aside>
      <div
        role="region"
        aria-label="Mobile workspace controls"
        className="sticky top-0 z-30 flex items-center justify-between gap-[var(--space-3)] border-b border-border bg-surface/90 px-[var(--space-4)] py-[var(--space-2)] backdrop-blur lg:hidden"
      >
        <Logo sub={props.sub} />
        <div className="flex items-center gap-1">
          <ThemeToggle />
          <button
            type="button"
            aria-label="Open menu"
            onClick={() => setOpen(true)}
            className="grid size-[var(--control-height)] place-items-center rounded-[var(--control-radius)] text-muted hover:bg-hover"
          >
            <Menu className="size-5" />
          </button>
        </div>
      </div>
      <Sheet open={open} onOpenChange={setOpen} label="Navigation">
        <Panel {...props} onNavigate={() => setOpen(false)} />
      </Sheet>
    </>
  );
}
