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
        <header className="sticky top-0 z-20 flex min-h-16 items-center justify-between gap-[var(--space-3)] border-b border-border bg-surface/90 px-[var(--space-4)] py-[var(--space-2)] backdrop-blur sm:px-[var(--space-6)] xl:px-[var(--space-7)]">
          <div className="flex min-w-0 items-center gap-[var(--space-2)] text-xs leading-snug text-muted">
            <span>AINS</span>
            <span aria-hidden="true">/</span>
            <span className="truncate font-medium text-foreground">{auditor ? "Audit operations" : "Your engagement"}</span>
          </div>
          <div className="flex shrink-0 items-center gap-[var(--space-2)]">
            <CommandPalette items={items} />
            <div className="hidden lg:block"><ThemeToggle /></div>
          </div>
        </header>
        <main
          id="main-content"
          tabIndex={-1}
          className="min-h-[calc(100vh-4rem)] bg-background"
        >
          <div className="mx-auto w-full max-w-[1440px] px-[var(--space-4)] py-[var(--space-5)] sm:px-[var(--space-6)] sm:py-[var(--space-6)] xl:px-[var(--space-7)]">
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
    <div className="mb-[var(--space-6)] flex flex-col items-start justify-between gap-[var(--space-4)] sm:flex-row sm:flex-wrap">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-[var(--space-3)]">
          <h1 className="type-display text-foreground">
            {title}
          </h1>
          {badge}
        </div>
        {description ? (
          <p className="mt-[var(--space-2)] max-w-3xl text-sm leading-normal text-muted">
            {description}
          </p>
        ) : null}
      </div>
      {actions ? (
        <div className="flex w-full shrink-0 flex-wrap items-center gap-[var(--space-2)] sm:w-auto">
          {actions}
        </div>
      ) : null}
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
        "rounded-xl border border-border bg-surface p-[var(--space-4)] shadow-[0_1px_2px_rgba(16,24,40,0.03)] sm:p-[var(--space-5)]",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="type-caption font-medium text-muted">{label}</div>
        {icon ? (
          <div className="grid size-8 place-items-center rounded-md bg-elevated text-muted">
            {icon}
          </div>
        ) : null}
      </div>
      <div className="type-metric mt-[var(--space-3)] text-foreground">
        {value}
      </div>
      {hint ? <div className="type-caption mt-[var(--space-2)] text-muted">{hint}</div> : null}
    </div>
  );
}
