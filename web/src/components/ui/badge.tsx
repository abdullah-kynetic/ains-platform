import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

export const badgeVariants = cva(
    "inline-flex items-center h-5 gap-1 rounded-full border px-2 py-0.5 text-xs font-medium leading-snug whitespace-nowrap",
  {
    variants: {
      variant: {
        default: "border-border bg-elevated text-muted",
        brand: "border-border-strong/50 bg-surface text-foreground",
        success: "border-success/20 bg-success/10 text-success-foreground",
        warning: "border-warning/20 bg-warning/10 text-warning-foreground",
        danger: "border-danger/20 bg-danger/10 text-danger-foreground",
        info: "border-info/20 bg-info/10 text-info-foreground",
        deadline: "border-deadline/30 bg-deadline/15 text-deadline-foreground",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export function Badge({ className, variant, dot, children, ...props }: React.HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants> & { dot?: boolean }) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props}>
      {dot ? <span className="size-1.5 rounded-full bg-current" /> : null}
      {children}
    </span>
  );
}
