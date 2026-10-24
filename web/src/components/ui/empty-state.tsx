import * as React from "react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: {
  icon: LucideIcon;
  title: string;
  description?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border border-dashed border-border-strong px-[var(--space-5)] py-[var(--space-8)] text-center",
        className,
      )}
    >
      <div className="mb-[var(--space-3)] flex size-11 items-center justify-center rounded-xl border border-brand/30 bg-brand-tint text-brand">
        <Icon className="size-5" />
      </div>
      <p className="text-sm font-semibold leading-snug">{title}</p>
      {description ? (
        <p className="mt-[var(--space-2)] max-w-sm text-sm leading-normal text-muted">
          {description}
        </p>
      ) : null}
      {action ? <div className="mt-[var(--space-4)]">{action}</div> : null}
    </div>
  );
}
