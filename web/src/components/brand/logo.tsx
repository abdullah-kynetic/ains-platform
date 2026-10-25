import { productName } from "@/lib/brand";
import { cn } from "@/lib/utils";

/** Kien product mark. The company name is Kien Solutions. */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={cn("size-7", className)} aria-hidden>
      <rect width="32" height="32" rx="7" className="fill-foreground" />
      <path
        d="M10 7.5v17M10 16h7.2M17.2 16 23.5 7.5M17.2 16 23.5 24.5"
        className="stroke-background"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
}

export function Logo({ className, sub }: { className?: string; sub?: string }) {
  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      <LogoMark />
      <div className="leading-tight">
        <div className="text-[15px] font-semibold tracking-[-0.02em]">{productName}</div>
        {sub ? <div className="text-[10px] uppercase tracking-[0.14em] text-subtle">{sub}</div> : null}
      </div>
    </div>
  );
}
