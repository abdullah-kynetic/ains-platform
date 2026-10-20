import { cn } from "@/lib/utils";

/** Placeholder wordmark until the brand name is chosen. */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={cn("size-7", className)} aria-hidden>
      <rect width="32" height="32" rx="8" className="fill-brand" />
      <path d="M9 23l7-14 7 14M11.5 18h9" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" fill="none" />
    </svg>
  );
}

export function Logo({ className, sub }: { className?: string; sub?: string }) {
  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      <LogoMark />
      <div className="leading-tight">
        <div className="text-[15px] font-semibold tracking-tight">AINS</div>
        {sub ? <div className="text-[10px] uppercase tracking-[0.14em] text-subtle">{sub}</div> : null}
      </div>
    </div>
  );
}
