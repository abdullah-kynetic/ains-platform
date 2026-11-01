/**
 * Tiny persisted store for synthetic frontend data. Browser-only (localStorage);
 * falls back to in-memory when storage is blocked. Replaced wholesale when the
 * real API exists: nothing outside `src/lib/api/*` should import this.
 */
const memory = new Map<string, unknown>();

export function readStore<T>(key: string, seed: () => T): T {
  if (memory.has(key)) return memory.get(key) as T;
  let value: T | undefined;
  try {
    const raw = typeof window !== "undefined" ? window.localStorage.getItem(key) : null;
    if (raw) value = JSON.parse(raw) as T;
  } catch {
    value = undefined;
  }
  if (value === undefined) value = seed();
  memory.set(key, value);
  return value;
}

export function writeStore<T>(key: string, value: T): T {
  memory.set(key, value);
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage blocked: keep the in-memory copy */
  }
  return value;
}

export function updateStore<T>(key: string, seed: () => T, change: (draft: T) => T | void): T {
  const draft = structuredClone(readStore(key, seed));
  const next = change(draft) ?? draft;
  return writeStore(key, next);
}

export const delay = <T,>(value: T, ms = 120) =>
  new Promise<T>((resolve) => setTimeout(() => resolve(structuredClone(value)), ms));

export const NOW = "2026-11-01T09:00:00.000Z";
export const uid = (prefix: string) => `${prefix}-${Math.random().toString(36).slice(2, 9)}`;
