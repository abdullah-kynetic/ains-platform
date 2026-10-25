import { cn } from "@/lib/utils";

export function Progress({
  value,
  className,
  tone = "brand",
  label = "Document collection progress",
}: {
  value: number;
  className?: string;
  tone?: "brand" | "warning" | "danger";
  label?: string;
}) {
  const v = Math.max(0, Math.min(100, value));
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(v)}
      className={cn("h-2 w-full overflow-hidden rounded-full bg-elevated", className)}
    >
      <div
        className={cn(
          "progress-fill h-full rounded-full",
          tone === "brand" && "bg-brand",
          tone === "warning" && "bg-warning",
          tone === "danger" && "bg-danger",
        )}
        style={{ width: `${v}%` }}
      />
    </div>
  );
}
