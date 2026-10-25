"use client";

import { useEffect, useSyncExternalStore, type CSSProperties } from "react";

type Theme = "light" | "dark" | "system";
type EffectiveTheme = "light" | "dark";
let pendingTheme: EffectiveTheme | undefined;

function applyTheme(theme: EffectiveTheme) {
  const root = document.documentElement;
  root.classList.toggle("dark", theme === "dark");
  root.dataset.theme = theme;
  pendingTheme = undefined;
}

function transitionTheme(
  theme: EffectiveTheme,
  origin: { x: number; y: number },
) {
  const root = document.documentElement;
  if ((pendingTheme ?? root.dataset.theme) === theme) return;
  pendingTheme = theme;
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

function systemOrigin() {
  const buttons = document.querySelectorAll<HTMLButtonElement>(
    'button[aria-label="System theme"]',
  );
  for (const button of buttons) {
    const bounds = button.getBoundingClientRect();
    if (
      button.checkVisibility() &&
      bounds.width &&
      bounds.height &&
      bounds.bottom > 0 &&
      bounds.right > 0 &&
      bounds.top < window.innerHeight &&
      bounds.left < window.innerWidth
    ) {
      return {
        x: bounds.left + bounds.width / 2,
        y: bounds.top + bounds.height / 2,
      };
    }
  }
  return { x: window.innerWidth / 2, y: window.innerHeight / 2 };
}

function resolveTheme(theme: Theme): EffectiveTheme {
  return theme === "system"
    ? window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light"
    : theme;
}

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
    // Reconcile OS changes that occurred between the bootstrap script and hydration.
    if (!document.documentElement.dataset.theme) {
      applyTheme(resolveTheme(preference()));
    } else {
      transitionTheme(resolveTheme(preference()), systemOrigin());
    }
    const apply = () => {
      if (preference() === "system") {
        transitionTheme(media.matches ? "dark" : "light", systemOrigin());
      }
    };
    const syncPreference = (event: StorageEvent) => {
      if (event.key === "ains-theme" || event.key === null) {
        transitionTheme(resolveTheme(preference()), systemOrigin());
      }
    };
    media.addEventListener("change", apply);
    window.addEventListener("storage", syncPreference);
    return () => {
      media.removeEventListener("change", apply);
      window.removeEventListener("storage", syncPreference);
    };
  }, []);
  return (
    <div
      role="group"
      aria-label="Color theme"
      className="theme-control flex rounded-md border border-border bg-surface p-1"
      style={{ "--theme-index": ["light", "dark", "system"].indexOf(theme) } as CSSProperties}
    >
      <span aria-hidden="true" className="theme-indicator" />
      {(["light", "dark", "system"] as const).map((value) => (
        <button
          key={value}
          type="button"
          aria-label={`${value[0].toUpperCase()}${value.slice(1)} theme`}
          aria-pressed={theme === value}
          onClick={(event) => {
            const bounds = event.currentTarget.getBoundingClientRect();
            const keyboardActivation = event.detail === 0;
            transitionTheme(resolveTheme(value), {
              x: keyboardActivation
                ? bounds.left + bounds.width / 2
                : event.clientX,
              y: keyboardActivation
                ? bounds.top + bounds.height / 2
                : event.clientY,
            });
            try {
              localStorage.setItem("ains-theme", value);
            } catch {
              /* Storage may be unavailable. */
            }
            window.dispatchEvent(new Event("ains-theme-change"));
          }}
          className="min-h-8 min-w-0 flex-1 rounded px-2 text-xs capitalize text-foreground hover:bg-hover/40"
        >
          {value}
        </button>
      ))}
    </div>
  );
}
