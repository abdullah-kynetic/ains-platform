import * as React from "react";
import { cn } from "@/lib/utils";

/** `bare` drops the frame when the table already sits inside a bordered card or section. */
export function Table({ className, bare, ...props }: React.TableHTMLAttributes<HTMLTableElement> & { bare?: boolean }) {
  return (
    <div data-slot="table-frame" className={cn("relative w-full overflow-x-auto", !bare && "rounded-xl border border-border bg-surface")}>
      <table className={cn("w-full caption-bottom text-sm", className)} {...props} />
    </div>
  );
}
export function THead({ className, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) {
  return <thead className={cn("[&_tr]:border-b [&_tr]:border-border", className)} {...props} />;
}
export function TBody({ className, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody className={cn("[&_tr:last-child]:border-0", className)} {...props} />;
}
export function TR({ className, ...props }: React.HTMLAttributes<HTMLTableRowElement>) {
  return <tr className={cn("border-b border-border transition-colors hover:bg-elevated/60", className)} {...props} />;
}
export function TH({ className, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return <th className={cn("h-10 bg-elevated/60 px-3 text-left align-middle text-xs font-medium leading-snug text-muted whitespace-nowrap", className)} {...props} />;
}
export function TD({ className, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={cn("px-3 py-3 align-middle text-sm leading-normal text-foreground", className)} {...props} />;
}
