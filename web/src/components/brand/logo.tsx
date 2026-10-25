"use client";

import { useTenant } from "@/components/tenant/tenant-provider";
import { KIEN_MARK_SRC } from "@/lib/tenant";
import { cn } from "@/lib/utils";

/** Placeholder wordmark until a firm logo URL is available. */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={cn("size-7", className)} aria-hidden>
      <rect width="32" height="32" rx="7" className="fill-foreground" />
      <path d="M9 23l7-14 7 14M11.5 18h9" className="stroke-background" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" fill="none" />
    </svg>
  );
}

export function Logo({ className, sub }: { className?: string; sub?: string }) {
  const { slug, branding } = useTenant();
  return (
    <div className={cn("flex items-center gap-2.5", className)} data-firm-slug={slug}>
      {/* A null logo stays on the Kien mark. Remote logos are https URLs from the API. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={branding.logoUrl ?? KIEN_MARK_SRC}
        alt=""
        className="size-7 rounded-md"
      />
      <div className="leading-tight">
        <div className="text-[15px] font-semibold tracking-[-0.02em]">{branding.name}</div>
        {sub ? <div className="text-[10px] uppercase tracking-[0.14em] text-subtle">{sub}</div> : null}
      </div>
    </div>
  );
}
