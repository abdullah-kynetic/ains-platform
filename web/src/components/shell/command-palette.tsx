"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Search, ArrowUpRight, Sun, Moon } from "lucide-react";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import type { NavItem } from "./nav";

export function CommandPalette({ items }: { items: NavItem[] }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const input = useRef<HTMLInputElement>(null);
  const commands = useRef<HTMLDivElement>(null);
  const themes = ["light", "dark"].filter(
    (theme) => `${theme} theme`.includes(query.toLowerCase()) || !query,
  );
  const router = useRouter();
  const results = items.filter((item) =>
    item.label.toLowerCase().includes(query.toLowerCase()),
  );
  useEffect(() => {
    function shortcut(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((value) => !value);
        setQuery("");
      }
    }
    window.addEventListener("keydown", shortcut);
    return () => window.removeEventListener("keydown", shortcut);
  }, []);
  useEffect(() => {
    if (open) input.current?.focus();
  }, [open]);
  function navigate(href: string) {
    setOpen(false);
    router.push(href);
  }
  return (
    <>
      <div className="relative">
        <button
          type="button"
          onClick={() => {
            setQuery("");
            setOpen(true);
          }}
          className="flex h-[var(--control-height)] items-center gap-[var(--space-2)] rounded-[var(--control-radius)] border border-border bg-background px-[var(--space-3)] text-sm text-muted sm:pr-16"
        >
          <Search className="size-4" aria-hidden="true" />
          <span className="sr-only sm:not-sr-only">Search workspace</span>
        </button>
        <kbd
          aria-hidden="true"
          className="pointer-events-none absolute top-1/2 right-3 hidden -translate-y-1/2 rounded-[var(--control-radius)] border border-border bg-surface px-[var(--space-2)] py-[var(--space-1)] text-xs leading-none text-muted sm:block"
        >
          ⌘ K
        </kbd>
      </div>
      <Dialog
        open={open}
        onOpenChange={setOpen}
        title="Go to workspace"
        description="Find a page or change appearance. Use arrow keys or Tab to choose, then Enter to open."
      >
        <div
          ref={commands}
          onKeyDown={(event) => {
            const buttons = Array.from(
              commands.current?.querySelectorAll<HTMLButtonElement>(
                "[data-command]",
              ) ?? [],
            );
            if (event.key === "ArrowDown" || event.key === "ArrowUp") {
              event.preventDefault();
              const index = buttons.indexOf(
                document.activeElement as HTMLButtonElement,
              );
              const next =
                event.key === "ArrowDown"
                  ? (index + 1) % buttons.length
                  : index < 0
                    ? buttons.length - 1
                    : (index - 1 + buttons.length) % buttons.length;
              buttons[next]?.focus();
            } else if (
              event.key === "Enter" &&
              event.target === input.current
            ) {
              event.preventDefault();
              buttons[0]?.click();
            }
          }}
        >
          <Input
            ref={input}
            aria-label="Search pages"
            placeholder="Where would you like to go?"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <p className="mt-4 text-xs text-subtle" role="status">
            {results.length + themes.length} matching commands
          </p>
          <p className="mt-[var(--space-4)] text-xs font-semibold uppercase tracking-[0.08em] text-muted">
            Workspace pages
          </p>
          <div className="mt-2 grid gap-1">
            {results.map((item) => (
              <button
                data-command
                key={item.href}
                onClick={() => navigate(item.href)}
                className="flex items-center justify-between rounded-lg px-3 py-3 text-left text-sm hover:bg-brand-tint hover:text-brand"
              >
                {item.label}
                <ArrowUpRight className="size-4" aria-hidden="true" />
              </button>
            ))}
          </div>
          <div className="mt-4 border-t border-border pt-4">
            <p className="mb-[var(--space-2)] text-xs font-semibold uppercase tracking-[0.08em] text-muted">
              Appearance
            </p>
            <div className="flex gap-2">
              {themes.map((theme) => (
                <button
                  data-command
                  key={theme}
                  type="button"
                  className="flex flex-1 items-center gap-2 rounded-md border border-border px-3 py-2 text-sm hover:bg-hover"
                  onClick={() => {
                    document.documentElement.classList.toggle(
                      "dark",
                      theme === "dark",
                    );
                    document.documentElement.dataset.theme = theme;
                    localStorage.setItem("ains-theme", theme);
                    setOpen(false);
                  }}
                >
                  {theme === "light" ? (
                    <Sun className="size-4" />
                  ) : (
                    <Moon className="size-4" />
                  )}
                  {theme === "light" ? "Light theme" : "Dark theme"}
                </button>
              ))}
            </div>
          </div>
          {!results.length && !themes.length && (
            <p className="py-5 text-sm text-muted">
              No pages match. Try another search.
            </p>
          )}
        </div>
      </Dialog>
    </>
  );
}
