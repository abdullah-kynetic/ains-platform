"use client";
import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

/** Route-based tabs (each tab is a URL). Active when pathname matches exactly (or startsWith for non-root tabs). */
export function LinkTabs({ tabs, className }: { tabs: { href: string; label: string; exact?: boolean }[]; className?: string }) {
  const pathname = usePathname();
  return (
    <nav className={cn("-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0", className)} aria-label="Tabs">
      <div className="flex min-w-max gap-1 border-b border-border">
        {tabs.map((t) => {
          const active = t.exact ? pathname === t.href : pathname === t.href || pathname.startsWith(`${t.href}/`);
          return (
            <Link
              key={t.href}
              href={t.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "relative px-3 py-2.5 text-sm font-medium transition-colors",
                active ? "text-foreground" : "text-muted hover:text-foreground",
              )}
            >
              {t.label}
              {active ? <span className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-brand" /> : null}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

/** Simple in-page tabs. */
export function Tabs({ items, defaultValue, className }: { items: { value: string; label: string; content: React.ReactNode }[]; defaultValue?: string; className?: string }) {
  const [value, setValue] = React.useState(defaultValue ?? items[0]?.value);
  return (
    <div className={className}>
      <div role="tablist" className="inline-flex rounded-lg border border-border bg-surface p-1">
        {items.map((i) => (
          <button
            key={i.value}
            role="tab"
            type="button"
            aria-selected={value === i.value}
            onClick={() => setValue(i.value)}
            className={cn("rounded-md px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer",
              value === i.value ? "bg-elevated text-foreground" : "text-muted hover:text-foreground")}
          >
            {i.label}
          </button>
        ))}
      </div>
      <div className="mt-4">{items.find((i) => i.value === value)?.content}</div>
    </div>
  );
}
