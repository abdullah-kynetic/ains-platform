import * as React from "react";
import { cn } from "@/lib/utils";
import { fieldBase } from "./input";

export function Textarea({
  className,
  ...props
}: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        fieldBase,
        "min-h-24 py-[var(--space-3)] leading-relaxed",
        className,
      )}
      {...props}
    />
  );
}
