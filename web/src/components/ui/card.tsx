import * as React from "react";
import { cn } from "@/lib/utils";

export function Card({
  className,
  featured,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { featured?: boolean }) {
  return (
    <div
      data-slot="card"
      className={cn(
        "flex flex-col gap-4 overflow-hidden rounded-xl bg-card py-5 text-card-foreground border border-border shadow-card has-[[data-slot=card-footer]]:pb-0",
        featured
          ? "border-border-strong"
          : "",
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
        "flex flex-col gap-1.5 px-5",
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
        "content-heading text-base font-medium leading-snug text-foreground",
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
    <p className={cn("reading-prose text-sm leading-normal text-muted", className)} {...props} />
  );
}
export function CardContent({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("px-5", className)}
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
      data-slot="card-footer"
      className={cn(
        "flex items-center gap-2 rounded-b-xl border-t border-border bg-elevated/60 px-5 py-3",
        className,
      )}
      {...props}
    />
  );
}
