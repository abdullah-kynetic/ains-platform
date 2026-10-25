"use client";

import { createContext, useContext, useState } from "react";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import type { NavItem } from "./nav";
import { CommandPalette } from "./command-palette";
import { SiteFooter } from "@/components/brand/site-footer";

const SearchHostContext = createContext<
  ((node: HTMLSpanElement | null) => void) | null
>(null);

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
  const pathname = usePathname();
  const [searchHost, setSearchHost] = useState<HTMLSpanElement | null>(null);
  return (
    <SearchHostContext.Provider value={setSearchHost}>
      <div className="flex min-h-screen flex-col lg:flex-row">
        {sidebar}
        <CommandPalette items={items} host={searchHost} />
        <div className="flex min-h-screen min-w-0 flex-1 flex-col">
          <main
            id="main-content"
            tabIndex={-1}
            className="flex-1 bg-background"
          >
            <div className="mx-auto w-full max-w-[1440px] px-[var(--space-4)] py-[var(--space-5)] sm:px-[var(--space-6)] sm:py-[var(--space-6)] xl:px-[var(--space-7)]">
              <div key={pathname} className="page-enter">
                {children}
              </div>
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
    <div className="mb-[var(--space-6)] flex flex-col items-start justify-between gap-[var(--space-4)] sm:flex-row sm:flex-wrap">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-[var(--space-3)]">
          <h1 className="type-display text-foreground">{title}</h1>
          {badge}
        </div>
        {description ? (
          <p className="mt-[var(--space-2)] max-w-3xl text-sm leading-normal text-muted">
            {description}
          </p>
        ) : null}
      </div>
      {actions || setSearchHost ? (
        <div className="flex w-full shrink-0 flex-wrap items-center gap-[var(--space-2)] sm:w-auto">
          {setSearchHost ? (
            <span ref={setSearchHost} className="inline-flex" />
          ) : null}
          {actions}
        </div>
      ) : null}
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
        "surface-card rounded-xl border border-border bg-surface p-[var(--space-4)] shadow-card sm:p-[var(--space-5)]",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="type-label">{label}</div>
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
        <div className="type-caption mt-[var(--space-2)] text-muted">
          {hint}
        </div>
      ) : null}
    </div>
  );
}
