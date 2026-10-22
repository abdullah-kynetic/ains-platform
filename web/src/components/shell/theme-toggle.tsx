"use client";

import { Moon, Sun } from "lucide-react";

type Theme = "light" | "dark";

function applyTheme(theme: Theme) {
  document.documentElement.classList.toggle("dark", theme === "dark");
  localStorage.setItem("ains-theme", theme);
}

export function ThemeToggle() {
  return (
    <button
      type="button"
      aria-label="Toggle color theme"
      title="Toggle color theme"
      onClick={() => {
        const nextTheme: Theme = document.documentElement.classList.contains("dark") ? "light" : "dark";
        applyTheme(nextTheme);
      }}
      className="grid size-9 place-items-center rounded-md border border-border bg-surface text-muted shadow-[0_1px_2px_rgba(16,24,40,0.03)] transition-colors hover:bg-hover hover:text-foreground"
    >
      <span className="theme-icon-moon"><Moon className="size-4" /></span>
      <span className="theme-icon-sun"><Sun className="size-4" /></span>
    </button>
  );
}
