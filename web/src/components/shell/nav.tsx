"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import {
  Check,
  ChevronsUpDown,
  LogOut,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  ChevronRight,
  Plus,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import * as Icons from "lucide-react";
import { getClients, type ClientSummary } from "@/lib/workflow-api";
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
    name: "Kien Operations",
    type: "Internal workspace",
    mark: "KI",
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
  const [assigned, setAssigned] = useState<ClientSummary[] | null>(null);
  const [error, setError] = useState(false);
  const pathname = usePathname();
  useEffect(() => {
    if (!auditor || onWorkspaceChange) return;
    let cancelled = false;
    getClients()
      .then((clients) => {
        if (!cancelled) setAssigned(clients);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [auditor, onWorkspaceChange]);
  const active = workspaces[auditor ? 0 : 1];

  if (!auditor)
    return (
      <div className="flex min-h-[var(--control-height)] w-full items-center gap-[var(--space-3)] rounded-lg border border-border bg-surface p-[var(--space-2)] shadow-card">
        <span className="grid size-8 shrink-0 place-items-center rounded-md bg-foreground text-xs font-semibold tracking-wide text-background">
          {active.mark}
        </span>
        <span
          title={active.name}
          className="break-words text-sm font-semibold text-foreground"
        >
          {active.name}
        </span>
      </div>
    );

  if (!onWorkspaceChange) {
    const current = assigned?.find(
      (client) => pathname === `/auditor/engagements/${client.id}`,
    );
    return (
      <div className="relative">
        <button
          type="button"
          aria-label="Assigned workspaces"
          aria-expanded={open}
          onClick={() => setOpen(!open)}
          className="flex min-h-[var(--control-height)] w-full items-center justify-between gap-2 rounded-lg border border-border bg-surface p-2 text-left text-sm font-semibold shadow-card hover:bg-hover"
        >
          <span className="break-words">
            {current?.firmName ?? "Kien Operations"}
          </span>
          <ChevronsUpDown className="size-3.5 shrink-0 text-subtle" />
        </button>
        {open && (
          <div className="absolute left-0 right-0 top-[calc(100%+4px)] z-50 min-w-56 rounded-lg border border-border bg-surface p-1.5 shadow-pop">
            <p className="px-2 py-1.5 text-xs font-semibold text-subtle">
              Assigned workspaces
            </p>
            <Link
              href="/auditor"
              onClick={() => {
                setOpen(false);
                onNavigate?.();
              }}
              className="block rounded-md px-2 py-2 text-sm hover:bg-hover"
            >
              All client audits
            </Link>
            {assigned?.map((client) => (
              <Link
                key={client.id}
                href={`/auditor/engagements/${client.id}`}
                aria-current={current?.id === client.id ? "page" : undefined}
                onClick={() => {
                  setOpen(false);
                  onNavigate?.();
                }}
                className="block break-words rounded-md px-2 py-2 text-sm hover:bg-hover"
              >
                {client.firmName}
              </Link>
            ))}
            {!assigned && (
              <p role="status" className="px-2 py-2 text-xs text-muted">
                {error
                  ? "Could not load workspaces. Open all client audits to retry."
                  : "Loading workspaces…"}
              </p>
            )}
            {assigned?.length === 0 && (
              <p className="px-2 py-2 text-xs text-muted">
                No assigned engagements.
              </p>
            )}
            <Link
              href="/auditor/workspaces/new"
              onClick={() => {
                setOpen(false);
                onNavigate?.();
              }}
              className="block border-t border-border px-2 py-2 text-xs text-muted"
            >
              Add client workspace
            </Link>
          </div>
        )}
      </div>
    );
  }

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
        <div className="absolute left-0 right-0 top-[calc(100%+4px)] z-50 min-w-56 rounded-lg border border-border bg-surface p-1.5 shadow-pop">
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
  const pathname = usePathname().replace(/\/+$/, "") || "/";

  return (
    <nav aria-label="Main navigation" className="grid gap-1">
      {items.map((item) => {
        const Icon = Icons[item.icon] as LucideIcon;
        const active =
          item.href === "/auditor" && pathname === "/"
            ? true
            : item.exact || item.href === "/" || item.href === "/auditor"
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
              "flex h-8 items-center gap-2 rounded-md p-2 text-sm leading-snug transition-colors",
              active
                ? "bg-sidebar-accent font-medium text-sidebar-accent-foreground"
                : "text-muted hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
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
    <div
      className={cn(
        "sidebar-panel flex min-h-0 flex-1 flex-col p-2",
        !desktop && "h-full",
      )}
    >
      <div className="sidebar-workspace shrink-0">
        {!desktop ? <Logo sub={sub} className="px-2 pt-2 pb-5" /> : null}
        <WorkspaceSwitcher
          auditor={auditor}
          onWorkspaceChange={onWorkspaceChange}
          onNavigate={onNavigate}
        />
      </div>
      <div className="sidebar-navigation min-h-0 flex-1 overflow-x-hidden overflow-y-auto">
        <p className="mt-2 flex h-8 items-center rounded-md px-2 text-xs font-medium text-sidebar-foreground/80">
          {auditor ? "Review" : "Engagement"}
        </p>
        <Items items={items} onNavigate={onNavigate} />
      </div>
      <div className="sidebar-theme shrink-0 pt-2">
        <ThemeToggle />
      </div>
      <div className="sidebar-identity mt-2 flex shrink-0 items-center gap-2 border-t border-sidebar-border px-0 pt-2">
        <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-elevated text-xs font-semibold text-muted">
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
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [width, setWidth] = useState(256);
  const [dragging, setDragging] = useState(false);
  const [restored, setRestored] = useState(false);
  const drag = useRef<{ pointer: number; start: number; width: number } | null>(
    null,
  );
  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      try {
        const saved = JSON.parse(
          localStorage.getItem("kien-sidebar") ?? "null",
        );
        if (
          saved &&
          typeof saved.width === "number" &&
          Number.isFinite(saved.width)
        ) {
          setWidth(Math.max(200, Math.min(360, saved.width)));
          setCollapsed(saved.collapsed === true);
        }
      } catch {
        /* Use defaults if storage is unavailable. */
      }
      setRestored(true);
    });
    return () => cancelAnimationFrame(frame);
  }, []);
  useEffect(() => {
    if (restored) {
      try {
        localStorage.setItem(
          "kien-sidebar",
          JSON.stringify({ width, collapsed }),
        );
      } catch {
        /* Resizing works without storage. */
      }
    }
  }, [width, collapsed, restored]);

  useEffect(() => {
    const toggle = () => setCollapsed((value) => !value);
    window.addEventListener("kien-toggle-sidebar", toggle);
    return () => window.removeEventListener("kien-toggle-sidebar", toggle);
  }, []);

  return (
    <>
      <aside
        data-collapsed={collapsed}
        data-dragging={dragging}
        style={{ width: collapsed ? 48 : width }}
        className="desktop-sidebar sticky top-0 hidden h-dvh min-h-screen self-start w-64 shrink-0 border-r border-sidebar-border bg-sidebar lg:flex lg:flex-col"
      >
        <div className="flex items-center justify-between gap-1 p-2">
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
        <div
          role="separator"
          aria-label="Resize sidebar"
          aria-orientation="vertical"
          aria-valuemin={200}
          aria-valuemax={360}
          aria-valuenow={width}
          aria-valuetext={collapsed ? "Collapsed" : `${width} pixels`}
          tabIndex={0}
          className="absolute inset-y-0 -right-1 z-40 w-2 cursor-col-resize touch-none hover:bg-brand/20 focus-visible:bg-brand/20 focus-visible:outline-2 focus-visible:outline-brand"
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === "Home") {
              event.preventDefault();
              setCollapsed((value) => !value);
            } else if (
              event.key === "ArrowLeft" ||
              event.key === "ArrowRight"
            ) {
              event.preventDefault();
              setCollapsed(false);
              setWidth((value) =>
                Math.max(
                  200,
                  Math.min(360, value + (event.key === "ArrowLeft" ? -16 : 16)),
                ),
              );
            }
          }}
          onPointerDown={(event) => {
            if (
              event.button !== 0 ||
              !window.matchMedia("(min-width: 1024px)").matches
            )
              return;
            event.preventDefault();
            event.currentTarget.setPointerCapture(event.pointerId);
            drag.current = {
              pointer: event.pointerId,
              start: event.clientX,
              width: collapsed ? 48 : width,
            };
            setDragging(true);
          }}
          onPointerMove={(event) => {
            const current = drag.current;
            if (!current || current.pointer !== event.pointerId) return;
            const next = current.width + event.clientX - current.start;
            setCollapsed(next < 140);
            if (next >= 140) setWidth(Math.max(200, Math.min(360, next)));
          }}
          onPointerUp={(event) => {
            if (drag.current?.pointer !== event.pointerId) return;
            drag.current = null;
            setDragging(false);
            event.currentTarget.releasePointerCapture(event.pointerId);
          }}
          onPointerCancel={() => {
            drag.current = null;
            setDragging(false);
          }}
          onLostPointerCapture={() => {
            drag.current = null;
            setDragging(false);
          }}
        />
      </aside>
      <div
        role="region"
        aria-label="Mobile workspace controls"
        className="sticky top-0 z-20 flex h-16 shrink-0 items-center gap-2 bg-background/60 px-4 backdrop-blur-md md:h-14 lg:hidden"
      >
        <button
          type="button"
          aria-label="Open menu"
          onClick={() => setOpen(true)}
          className="-ml-1 grid size-8 shrink-0 place-items-center rounded-lg text-muted hover:bg-hover"
        >
          <Menu aria-hidden className="size-4" />
        </button>
        <span aria-hidden className="mr-2 h-4 border-r border-border" />
        <span className="text-sm text-muted">{props.sub}</span>
        <ChevronRight aria-hidden className="size-3.5 shrink-0 text-subtle" />
        <span className="truncate text-sm">{props.items.find((item) => item.href === pathname)?.label ?? "Workspace"}</span>
      </div>
      <Sheet open={open} onOpenChange={setOpen} label="Navigation">
        <Panel {...props} onNavigate={() => setOpen(false)} />
      </Sheet>
    </>
  );
}
