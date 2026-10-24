import { cn } from "@/lib/utils";
import type { NavItem } from "./nav";
import { CommandPalette } from "./command-palette";
import { ThemeToggle } from "@/components/shell/theme-toggle";

export function Shell({
  sidebar,
  children,
  items,
  auditor,
}: {
  sidebar: React.ReactNode;
  items: NavItem[];
  auditor: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      {sidebar}
      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-20 flex min-h-16 items-center justify-between border-b border-border bg-surface/90 px-8 backdrop-blur">
          <div className="flex items-center gap-2 text-xs text-subtle">
            <span>Kien</span>
            <span>/</span>
            <span className="font-medium text-muted">{auditor ? "Audit operations" : "Your engagement"}</span>
          </div>
          <div className="flex items-center gap-2">
            <CommandPalette items={items} />
            <div className="hidden lg:block"><ThemeToggle /></div>
          </div>
        </header>
        <main
          id="main-content"
          tabIndex={-1}
          className="min-h-[calc(100vh-4rem)] bg-background"
        >
          <div className="mx-auto w-full max-w-[1440px] px-4 py-6 sm:px-8 sm:py-8 xl:px-10">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}

export function PageHeader({
  title,
  description,
  actions,
  badge,
}: {
  title: string;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  badge?: React.ReactNode;
}) {
  return (
    <div className="mb-7 flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-[26px] font-semibold tracking-[-0.035em] text-foreground">
            {title}
          </h1>
          {badge}
        </div>
        {description ? (
          <p className="mt-1.5 max-w-3xl text-sm leading-6 text-muted">
            {description}
          </p>
        ) : null}
      </div>
      {actions}
    </div>
  );
}

export function Stat({
  label,
  value,
  hint,
  icon,
  className,
}: {
  label: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
  icon?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-surface p-5 shadow-[0_1px_2px_rgba(16,24,40,0.03)]",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="text-xs font-medium text-muted">{label}</div>
        {icon ? (
          <div className="grid size-8 place-items-center rounded-md bg-elevated text-muted">
            {icon}
          </div>
        ) : null}
      </div>
      <div className="mt-3 text-[26px] font-semibold tabular-nums tracking-[-0.04em] text-foreground">
        {value}
      </div>
      {hint ? <div className="mt-1.5 text-[11px] text-subtle">{hint}</div> : null}
    </div>
  );
}
