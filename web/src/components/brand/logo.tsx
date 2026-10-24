import { cn } from "@/lib/utils";

/** Placeholder wordmark until the brand name is chosen. */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={cn("size-7", className)} aria-hidden>
      <rect width="32" height="32" rx="7" className="fill-foreground" />
      <path d="M9 23l7-14 7 14M11.5 18h9" className="stroke-background" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" fill="none" />
    </svg>
  );
}

export function Logo({ className, sub }: { className?: string; sub?: string }) {
  return (
    <div className={cn("flex items-center gap-[var(--space-3)]", className)}>
      <LogoMark />
      <div className="leading-tight">
        <div className="text-base font-semibold tracking-[-0.02em]">AINS</div>
        {sub ? <div className="text-xs font-medium uppercase tracking-[0.08em] text-muted">{sub}</div> : null}
      </div>
    </div>
  );
}
