import * as React from "react";
import { cn } from "@/lib/utils";

export function Card({
  className,
  featured,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { featured?: boolean }) {
  return (
    <div
      className={cn(
        "rounded-card border bg-surface shadow-card",
        featured
          ? "border-brand/30 shadow-featured"
          : "border-border",
        className,
      )}
      {...props}
    />
  );
}
export function CardHeader({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "flex flex-col gap-[var(--space-2)] px-[var(--space-5)] pt-[var(--space-5)] pb-[var(--space-3)]",
        className,
      )}
      {...props}
    />
  );
}
export function CardTitle({
  className,
  ...props
}: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h2
      className={cn(
        "text-sm font-semibold leading-snug tracking-[-0.01em] text-foreground",
        className,
      )}
      {...props}
    />
  );
}
export function CardDescription({
  className,
  ...props
}: React.HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p className={cn("text-sm leading-normal text-muted", className)} {...props} />
  );
}
export function CardContent({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("px-[var(--space-5)] pb-[var(--space-5)]", className)}
      {...props}
    />
  );
}
export function CardFooter({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "flex items-center gap-[var(--space-2)] border-t border-border px-[var(--space-5)] py-[var(--space-3)]",
        className,
      )}
      {...props}
    />
  );
}
