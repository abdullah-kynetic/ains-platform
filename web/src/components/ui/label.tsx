import * as React from "react";
import { cn } from "@/lib/utils";

export function Label({ className, ...props }: React.LabelHTMLAttributes<HTMLLabelElement>) {
  return (
    <label
      className={cn("text-sm font-medium leading-snug text-foreground", className)}
      {...props}
    />
  );
}

export function Field({
  label,
  htmlFor,
  hint,
  children,
  className,
}: {
  label: string;
  htmlFor?: string;
  hint?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  const generated = React.useId();
  const only = React.Children.count(children) === 1 && React.isValidElement<{ id?: string }>(children) ? children : null;
  const id = htmlFor ?? only?.props.id ?? generated;
  return (
    <div className={cn("grid gap-[var(--space-2)]", className)}>
      <Label htmlFor={id}>{label}</Label>
      {only && !only.props.id && !htmlFor ? React.cloneElement(only, { id }) : children}
      {hint ? <p className="type-caption text-muted">{hint}</p> : null}
    </div>
  );
}
