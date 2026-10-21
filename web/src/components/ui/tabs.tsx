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
export function Tabs({ items, defaultValue, className, onValueChange }: { items: { value: string; label: string; content: React.ReactNode }[]; defaultValue?: string; className?: string; onValueChange?: (value: string) => void }) {
  const [value, setValue] = React.useState(defaultValue ?? items[0]?.value);
  const id = React.useId();
  function select(next: string) { setValue(next); onValueChange?.(next); }
  return (
    <div className={className}>
      <div role="tablist" className="inline-flex rounded-lg border border-border bg-surface p-1">
        {items.map((i, index) => (
          <button
            key={i.value}
            role="tab"
            id={`${id}-tab-${i.value}`}
            aria-controls={`${id}-panel-${i.value}`}
            tabIndex={value === i.value ? 0 : -1}
            type="button"
            aria-selected={value === i.value}
            onClick={() => select(i.value)}
            onKeyDown={(event) => {
              const nextIndex = event.key === "ArrowRight" ? (index + 1) % items.length
                : event.key === "ArrowLeft" ? (index - 1 + items.length) % items.length
                : event.key === "Home" ? 0 : event.key === "End" ? items.length - 1 : -1;
              if (nextIndex < 0) return;
              event.preventDefault(); select(items[nextIndex].value);
              document.getElementById(`${id}-tab-${items[nextIndex].value}`)?.focus();
            }}
            className={cn("rounded-md px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer",
              value === i.value ? "bg-elevated text-foreground" : "text-muted hover:text-foreground")}
          >
            {i.label}
          </button>
        ))}
      </div>
      <div className="mt-4" role="tabpanel" id={`${id}-panel-${value}`} aria-labelledby={`${id}-tab-${value}`}>{items.find((i) => i.value === value)?.content}</div>
    </div>
  );
}
