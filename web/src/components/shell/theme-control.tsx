"use client";

import { useEffect, useSyncExternalStore } from "react";
import { Select } from "@/components/ui/select";

type Theme = "system" | "light" | "dark";
const eventName = "ains-theme-changed";
function getTheme(): Theme {
  const value = localStorage.getItem("ains-theme");
  return value === "dark" || value === "light" ? value : "system";
}
function subscribe(callback: () => void) {
  window.addEventListener(eventName, callback);
  window.addEventListener("storage", callback);
  return () => { window.removeEventListener(eventName, callback); window.removeEventListener("storage", callback); };
}

export function ThemeControl() {
  const theme = useSyncExternalStore(subscribe, getTheme, () => "system" as Theme);
  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => { document.documentElement.dataset.theme = theme === "system" ? (media.matches ? "dark" : "light") : theme; };
    apply(); media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, [theme]);
  return <div className="mb-4 ml-auto w-40"><Select aria-label="Color theme" value={theme} onChange={(event) => {
    localStorage.setItem("ains-theme", event.target.value); window.dispatchEvent(new Event(eventName));
  }}><option value="system">System theme</option><option value="light">Light theme</option><option value="dark">Dark theme</option></Select></div>;
}
