"use client";

import { createContext, useContext, useState } from "react";
import { cn } from "@/lib/utils";
import type { NavItem } from "./nav";
import { CommandPalette } from "./command-palette";
import { SiteFooter } from "@/components/brand/site-footer";

const SearchHostContext = createContext<(host: HTMLDivElement | null) => void>(
  () => {},
);

export function Shell({
  sidebar,
  children,
  items,
}: {
  sidebar: React.ReactNode;
  items: NavItem[];
  auditor: boolean;
  children: React.ReactNode;
}) {
  const [searchHost, setSearchHost] = useState<HTMLDivElement | null>(null);
  return (
    <SearchHostContext.Provider value={setSearchHost}>
      <CommandPalette items={items} triggerHost={searchHost} />
      <div className="workspace-shell flex min-h-screen flex-col">
        {sidebar}
        <div className="flex min-h-screen min-w-0 flex-1 flex-col">
          <main
            id="main-content"
            tabIndex={-1}
            className="workspace-canvas flex-1 bg-background"
          >
            <div className="flex w-full flex-col px-4 pt-2 pb-4 md:px-6 md:pt-4">
              {children}
            </div>
          </main>
          <SiteFooter />
        </div>
      </div>
    </SearchHostContext.Provider>
  );
}

export function PageHeader({
  title,
  description,
  actions,
  badge,
}: {
  title: string;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  badge?: React.ReactNode;
}) {
  const setSearchHost = useContext(SearchHostContext);
  return (
    <div
      data-page-header
      className="mb-4 flex flex-col items-start justify-between gap-4 sm:flex-row"
    >
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-[var(--space-3)]">
          <h1 className="content-heading type-display text-foreground">{title}</h1>
          {badge}
        </div>
        {description ? (
          <p className="reading-prose mt-1 text-sm leading-normal text-muted">
            {description}
          </p>
        ) : null}
      </div>
      <div className="flex w-full shrink-0 flex-wrap items-center justify-end gap-[var(--space-2)] sm:w-auto sm:max-w-full">
        <div ref={setSearchHost} />
        {actions}
      </div>
    </div>
  );
}

export function Stat({
  label,
  value,
  hint,
  icon,
  className,
}: {
  label: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
  icon?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "stat-card rounded-xl bg-card p-4 shadow-card ring-1 ring-foreground/10",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="text-sm text-muted">{label}</div>
        {icon ? (
          <div className="grid size-8 place-items-center rounded-md bg-elevated text-muted">
            {icon}
          </div>
        ) : null}
      </div>
      <div className="type-metric mt-[var(--space-3)] text-foreground">
        {value}
      </div>
      {hint ? (
        <div className="mt-2 text-sm text-muted">
          {hint}
        </div>
      ) : null}
    </div>
  );
}
