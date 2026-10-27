"use client";
import * as React from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

function useModal(open: boolean) {
  const panel = React.useRef<HTMLDialogElement>(null);
  React.useEffect(() => {
    const dialog = panel.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
      if (dialog.open) dialog.close();
    };
  }, [open]);
  return panel;
}

type DialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  dismissible?: boolean;
};

function trapFocus(event: React.KeyboardEvent<HTMLDialogElement>) {
  if (event.key !== "Tab") return;
  const controls = event.currentTarget.querySelectorAll<HTMLElement>(
    'a[href], button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex="0"]',
  );
  const first = controls[0];
  const last = controls[controls.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last?.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first?.focus();
  }
}

export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  children,
  className,
  dismissible = true,
}: DialogProps) {
  const panel = useModal(open);
  if (typeof document === "undefined") return null;
  return createPortal(
    <dialog
      ref={panel}
      onKeyDown={trapFocus}
      aria-label={title}
      onCancel={(event) => {
        event.preventDefault();
        if (dismissible) onOpenChange(false);
      }}
      className={cn(
        "fixed inset-0 m-auto max-h-[90dvh] w-[calc(100%-var(--space-6))] max-w-lg overflow-y-auto rounded-xl border border-border bg-surface p-4 text-foreground shadow-overlay",
        className,
      )}
    >
      <div className="mb-[var(--space-4)] flex items-start justify-between gap-[var(--space-4)]">
        <div>
          <h2 className="text-base font-medium leading-snug">{title}</h2>
          {description && (
            <p className="mt-[var(--space-2)] text-sm leading-normal text-muted">
              {description}
            </p>
          )}
        </div>
        {dismissible && (
          <button
            aria-label="Close"
            onClick={() => onOpenChange(false)}
            className="rounded-lg p-2"
          >
            <X aria-hidden className="size-5" />
          </button>
        )}
      </div>
      {children}
    </dialog>,
    document.body,
  );
}

/** Native modal supplies focus trapping, background inertness and focus return. */
export function Sheet({
  open,
  onOpenChange,
  children,
  side = "left",
  label,
  className,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: React.ReactNode;
  side?: "left" | "right";
  label: string;
  className?: string;
}) {
  const panel = useModal(open);
  if (typeof document === "undefined") return null;
  return createPortal(
    <dialog
      ref={panel}
      onKeyDown={trapFocus}
      aria-label={label}
      onCancel={(event) => {
        event.preventDefault();
        onOpenChange(false);
      }}
      className={cn(
        "fixed inset-y-0 m-0 h-dvh max-h-none w-72 max-w-[85vw] overflow-y-auto border border-border bg-background pt-10 text-foreground shadow-overlay",
        side === "left" ? "left-0 right-auto" : "left-auto right-0",
        className,
      )}
    >
      <button
        aria-label={side === "left" ? "Close navigation" : "Close record"}
        onClick={() => onOpenChange(false)}
        className="absolute right-3 top-2 rounded-lg p-2"
      >
        <X aria-hidden className="size-5" />
      </button>
      {children}
    </dialog>,
    document.body,
  );
}
