"use client";

import { Moon, Sun } from "lucide-react";

type Theme = "light" | "dark";

function applyTheme(theme: Theme) {
  document.documentElement.classList.toggle("dark", theme === "dark");
  localStorage.setItem("ains-theme", theme);
}

function transitionTheme(
  theme: Theme,
  origin: { x: number; y: number },
) {
  const root = document.documentElement;
  const reduceMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)",
  ).matches;

  if (!document.startViewTransition || reduceMotion) {
    applyTheme(theme);
    return;
  }

  root.style.setProperty("--theme-transition-x", `${origin.x}px`);
  root.style.setProperty("--theme-transition-y", `${origin.y}px`);

  const transition = document.startViewTransition(() => applyTheme(theme));
  void transition.finished.finally(() => {
    root.style.removeProperty("--theme-transition-x");
    root.style.removeProperty("--theme-transition-y");
  });
}

export function ThemeToggle() {
  return (
    <button
      type="button"
      aria-label="Toggle color theme"
      title="Toggle color theme"
      onClick={(event) => {
        const nextTheme: Theme = document.documentElement.classList.contains(
          "dark",
        )
          ? "light"
          : "dark";
        const bounds = event.currentTarget.getBoundingClientRect();
        const keyboardActivation = event.detail === 0;

        transitionTheme(nextTheme, {
          x: keyboardActivation
            ? bounds.left + bounds.width / 2
            : event.clientX,
          y: keyboardActivation
            ? bounds.top + bounds.height / 2
            : event.clientY,
        });
      }}
      className="grid size-9 place-items-center rounded-md border border-border bg-surface text-muted shadow-[0_1px_2px_rgba(16,24,40,0.03)] transition-colors hover:bg-hover hover:text-foreground"
    >
      <span className="theme-icon-moon">
        <Moon className="size-4" />
      </span>
      <span className="theme-icon-sun">
        <Sun className="size-4" />
      </span>
    </button>
  );
}
