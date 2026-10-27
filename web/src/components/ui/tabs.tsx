"use client";
import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

/** Route-based tabs (each tab is a URL). Active when pathname matches exactly (or startsWith for non-root tabs). */
export function LinkTabs({
  tabs,
  className,
}: {
  tabs: { href: string; label: string; exact?: boolean }[];
  className?: string;
}) {
  const pathname = usePathname();
  return (
    <nav
      className={cn("-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0", className)}
      aria-label="Tabs"
    >
      <div className="inline-flex h-8 min-w-max items-center gap-1 rounded-lg bg-elevated p-[3px]">
        {tabs.map((t) => {
          const active = t.exact
            ? pathname === t.href
            : pathname === t.href || pathname.startsWith(`${t.href}/`);
          return (
            <Link
              key={t.href}
              href={t.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "relative rounded-md px-1.5 py-0.5 text-sm font-medium transition-colors",
                active ? "bg-background text-foreground shadow-sm" : "text-muted hover:text-foreground",
              )}
            >
              {t.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

/** Simple in-page tabs. */
export function Tabs({
  items,
  defaultValue,
  className,
}: {
  items: { value: string; label: string; content: React.ReactNode }[];
  defaultValue?: string;
  className?: string;
}) {
  const [value, setValue] = React.useState(defaultValue ?? items[0]?.value);
  const id = React.useId();
  return (
    <div className={className}>
      <div
        role="tablist"
        className="inline-flex h-8 items-center rounded-lg bg-elevated p-[3px]"
      >
        {items.map((i, index) => (
          <button
            key={i.value}
            role="tab"
            type="button"
            aria-selected={value === i.value}
            id={`${id}-${i.value}`}
            aria-controls={`${id}-panel`}
            tabIndex={value === i.value ? 0 : -1}
            onKeyDown={(event) => {
              let next: number;
              if (event.key === "ArrowRight") next = (index + 1) % items.length;
              else if (event.key === "ArrowLeft")
                next = (index - 1 + items.length) % items.length;
              else if (event.key === "Home") next = 0;
              else if (event.key === "End") next = items.length - 1;
              else return;
              event.preventDefault();
              setValue(items[next].value);
              document.getElementById(`${id}-${items[next].value}`)?.focus();
            }}
            onClick={() => setValue(i.value)}
            className={cn(
              "min-h-0 rounded-md px-1.5 py-0.5 text-sm font-medium transition-colors cursor-pointer",
              value === i.value
                ? "bg-background text-foreground shadow-sm"
                : "text-muted hover:text-foreground",
            )}
          >
            {i.label}
          </button>
        ))}
      </div>
      <div
        id={`${id}-panel`}
        role="tabpanel"
        aria-labelledby={`${id}-${value}`}
        tabIndex={0}
        className="mt-4"
      >
        {items.find((i) => i.value === value)?.content}
      </div>
    </div>
  );
}
