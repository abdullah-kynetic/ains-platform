import * as React from "react";
import { cn } from "@/lib/utils";

export const fieldBase =
  "w-full rounded-[var(--control-radius)] border border-border-strong bg-surface px-[var(--space-3)] text-sm leading-normal text-foreground placeholder:text-muted control-motion hover:border-foreground/30 focus:border-ochre disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-danger-foreground";

export function Input({ className, ...props }: React.ComponentPropsWithRef<"input">) {
  return (
    <input
      className={cn(fieldBase, "h-[var(--control-height)]", className)}
      {...props}
    />
  );
}
