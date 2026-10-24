import { AlertCircle, LoaderCircle } from "lucide-react";
import { Button } from "./button";

export function LoadState({
  error,
  retry,
  label = "Loading your workspace…",
}: {
  error?: string | null;
  retry?: () => void;
  label?: string;
}) {
  return (
    <div
      role={error ? "alert" : "status"}
      className="grid min-h-48 place-content-center gap-[var(--space-4)] rounded-xl border border-border bg-surface px-[var(--space-5)] py-[var(--space-8)] text-center"
    >
      {error ? (
        <AlertCircle aria-hidden className="mx-auto size-8 text-warning-foreground" />
      ) : (
        <LoaderCircle
          aria-hidden
          className="mx-auto size-8 animate-spin text-brand"
        />
      )}
      <p className="text-sm font-medium leading-normal">
        {error ? "We couldn’t load this screen." : label}
      </p>
      {error ? (
        <p className="status-note mx-auto max-w-lg" data-tone="warning">
          {error}
        </p>
      ) : null}
      {error && retry ? (
        <Button variant="outline" onClick={retry}>
          Try again
        </Button>
      ) : null}
    </div>
  );
}
