import { cn } from "@/lib/utils";

export function StatusNote({
  tone,
  role,
  className,
  children,
}: {
  tone: "success" | "danger" | "warning" | "info";
  role?: "status" | "alert";
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <p role={role} data-tone={tone} className={cn("status-note", className)}>
      {children}
    </p>
  );
}
