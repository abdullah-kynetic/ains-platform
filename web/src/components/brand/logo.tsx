"use client";

import { useTenant } from "@/components/tenant/tenant-provider";
import { KIEN_MARK_SRC } from "@/lib/tenant";
import { cn } from "@/lib/utils";

/** Placeholder wordmark until a firm logo URL is available. */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={cn("size-7", className)} aria-hidden>
      <rect width="32" height="32" rx="7" className="fill-accent" />
      <path
        d="M10 7.5v17M10 16h7.2M17.2 16 23.5 7.5M17.2 16 23.5 24.5"
        className="stroke-on-accent"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
}

export function Logo({ className, sub }: { className?: string; sub?: string }) {
  const { slug, branding } = useTenant();
  return (
    <div className={cn("flex items-center gap-[var(--space-3)]", className)} data-firm-slug={slug}>
      {/* A null logo stays on the Kien mark. Remote logos are https URLs from the API. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={branding.logoUrl ?? KIEN_MARK_SRC}
        alt=""
        className="size-7 rounded-md"
      />
      <div className="leading-tight">
        <div className="text-base font-semibold tracking-[-0.02em]">{branding.name}</div>
        {sub ? <div className="text-xs font-medium uppercase tracking-[0.08em] text-muted">{sub}</div> : null}
      </div>
    </div>
  );
}
