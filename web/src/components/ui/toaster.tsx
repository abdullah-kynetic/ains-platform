"use client";
import { Toaster as Sonner } from "sonner";

export function Toaster() {
  return (
    <Sonner
      theme="dark"
      position="bottom-right"
      toastOptions={{
        classNames: {
          toast: "!bg-elevated !border !border-white/10 !text-foreground !rounded-xl",
          description: "!text-muted",
        },
      }}
    />
  );
}
