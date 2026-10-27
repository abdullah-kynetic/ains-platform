import * as React from "react";
import { cn } from "@/lib/utils";

export const fieldBase =
  "w-full rounded-[var(--control-radius)] border border-border-strong bg-surface px-2.5 py-1 text-base md:text-sm leading-normal text-foreground placeholder:text-muted transition-colors hover:border-foreground/30 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-danger-foreground";

export function Input({ className, ...props }: React.ComponentPropsWithRef<"input">) {
  return (
    <input
      className={cn(fieldBase, "h-8", className)}
      {...props}
    />
  );
}
