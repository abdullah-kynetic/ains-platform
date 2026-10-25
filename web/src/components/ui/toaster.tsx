"use client";
import { Toaster as Sonner } from "sonner";

export function Toaster() {
  return (
    <Sonner
      theme="system"
      position="bottom-right"
      toastOptions={{
        classNames: {
          toast: "!rounded-xl !border !border-border !bg-surface !text-foreground !shadow-pop !p-4",
          description: "!text-muted",
        },
      }}
    />
  );
}
