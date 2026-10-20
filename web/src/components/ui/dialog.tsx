"use client";
import * as React from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

type DialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  /** Prevent closing via overlay/Escape (e.g. copy-once secret). */
  dismissible?: boolean;
};

function useOverlay(open: boolean, close: () => void, dismissible: boolean) {
  React.useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape" && dismissible) close(); };
    window.addEventListener("keydown", onKey);
    return () => { document.body.style.overflow = prev; window.removeEventListener("keydown", onKey); };
  }, [open, close, dismissible]);
}

export function Dialog({ open, onOpenChange, title, description, children, className, dismissible = true }: DialogProps) {
  const close = React.useCallback(() => onOpenChange(false), [onOpenChange]);
  useOverlay(open, close, dismissible);
  const panel = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    if (open) panel.current?.querySelector<HTMLElement>("input,textarea,select,button:not([data-close])")?.focus();
  }, [open]);
  if (!open || typeof document === "undefined") return null;
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center sm:p-4">
      <div className="absolute inset-0 animate-fade-in bg-black/70 backdrop-blur-sm" onClick={dismissible ? close : undefined} />
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={cn("relative z-10 max-h-[90dvh] w-full overflow-y-auto rounded-t-2xl border border-border bg-surface p-5 shadow-2xl animate-pop-in sm:max-w-lg sm:rounded-2xl", className)}
      >
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold">{title}</h2>
            {description ? <p className="mt-1 text-sm text-muted">{description}</p> : null}
          </div>
          {dismissible ? (
            <button data-close type="button" onClick={close} className="rounded-md p-1 text-subtle hover:bg-white/5 hover:text-foreground cursor-pointer" aria-label="Close">
              <X className="size-4" />
            </button>
          ) : null}
        </div>
        {children}
      </div>
    </div>,
    document.body,
  );
}

/** Side sheet (used for the mobile nav). */
export function Sheet({ open, onOpenChange, children, side = "left", label }: { open: boolean; onOpenChange: (o: boolean) => void; children: React.ReactNode; side?: "left" | "right"; label: string }) {
  const close = React.useCallback(() => onOpenChange(false), [onOpenChange]);
  useOverlay(open, close, true);
  if (!open || typeof document === "undefined") return null;
  return createPortal(
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 animate-fade-in bg-black/70 backdrop-blur-sm" onClick={close} />
      <div role="dialog" aria-modal="true" aria-label={label}
        className={cn("absolute inset-y-0 w-72 max-w-[85vw] border-border bg-background shadow-2xl animate-slide-in", side === "left" ? "left-0 border-r" : "right-0 border-l")}>
        {children}
      </div>
    </div>,
    document.body,
  );
}
