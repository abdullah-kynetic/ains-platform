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
      className="grid min-h-48 place-content-center gap-4 rounded-xl border border-border bg-surface p-6 text-center"
    >
      {error ? (
        <AlertCircle aria-hidden className="mx-auto size-7 text-amber-300" />
      ) : (
        <LoaderCircle
          aria-hidden
          className="mx-auto size-7 animate-spin text-brand-hover"
        />
      )}
      <p>{error ? "We couldn’t load this screen." : label}</p>
      {error && (
        <p className="max-w-lg break-words text-sm text-muted">{error}</p>
      )}
      {error && retry && (
        <Button variant="outline" onClick={retry}>
          Try again
        </Button>
      )}
    </div>
  );
}
