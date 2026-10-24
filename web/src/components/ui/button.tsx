import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

export const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-[var(--control-radius)] text-sm font-medium leading-none transition-colors disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0 cursor-pointer",
  {
    variants: {
      variant: {
        default:
          "bg-accent text-on-accent hover:bg-accent-hover shadow-button",
        secondary:
          "bg-elevated text-foreground border border-border hover:bg-hover",
        outline:
          "border border-border-strong bg-surface text-foreground hover:bg-hover",
        ghost: "text-muted hover:bg-hover hover:text-foreground",
        destructive:
          "bg-danger/10 text-danger-foreground border border-danger/30 hover:bg-danger/15",
        link: "h-auto min-h-0 px-0 text-brand underline-offset-4 hover:underline",
      },
      size: {
        default: "h-[var(--control-height)] px-[var(--space-4)]",
        sm: "h-[var(--control-height)] px-[var(--space-3)]",
        lg: "h-[var(--control-height)] px-[var(--space-5)]",
        icon: "size-[var(--control-height)]",
        "icon-sm": "size-[var(--control-height)]",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants>;

export function Button({
  className,
  variant,
  size,
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  );
}
