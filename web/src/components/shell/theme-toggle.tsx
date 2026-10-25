"use client";

import { useEffect, useSyncExternalStore } from "react";

type Theme = "light" | "dark" | "system";
function preference(): Theme {
  try {
    const saved = localStorage.getItem("ains-theme");
    return saved === "light" || saved === "dark" ? saved : "system";
  } catch {
    return "system";
  }
}
function subscribe(listener: () => void) {
  window.addEventListener("storage", listener);
  window.addEventListener("ains-theme-change", listener);
  return () => {
    window.removeEventListener("storage", listener);
    window.removeEventListener("ains-theme-change", listener);
  };
}
export function ThemeToggle() {
  const theme = useSyncExternalStore(
    subscribe,
    preference,
    () => "system" as Theme,
  );
  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      const dark = theme === "dark" || (theme === "system" && media.matches);
      document.documentElement.classList.toggle("dark", dark);
      document.documentElement.dataset.theme = dark ? "dark" : "light";
    };
    apply();
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, [theme]);
  return (
    <div
      role="group"
      aria-label="Color theme"
      className="flex rounded-md border border-border bg-surface p-1"
    >
      {(["light", "dark", "system"] as const).map((value) => (
        <button
          key={value}
          type="button"
          aria-label={`${value[0].toUpperCase()}${value.slice(1)} theme`}
          aria-pressed={theme === value}
          onClick={() => {
            try {
              localStorage.setItem("ains-theme", value);
            } catch {
              /* Storage may be unavailable. */
            }
            window.dispatchEvent(new Event("ains-theme-change"));
          }}
          className={`min-h-8 min-w-0 flex-1 rounded px-2 text-xs capitalize text-foreground hover:bg-hover ${theme === value ? "bg-hover" : ""}`}
        >
          {value}
        </button>
      ))}
    </div>
  );
}
