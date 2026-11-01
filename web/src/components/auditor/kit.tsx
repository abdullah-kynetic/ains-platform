"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Info } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { LoadState } from "@/components/ui/load-state";
import type { Conclusion, FindingStatus, Severity } from "@/lib/api/index";

/** Loads data, exposes reload and a setter for optimistic updates. */
export function useAsync<T>(load: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [tick, setTick] = useState(0);
  const loader = useRef(load);
  useEffect(() => { loader.current = load; });
  const key = JSON.stringify(deps);
  useEffect(() => {
    let alive = true;
    loader.current()
      .then((value) => { if (alive) { setData(value); setError(""); } })
      .catch((e: Error) => { if (alive) setError(e.message || "Something went wrong."); });
    return () => { alive = false; };
  }, [key, tick]);
  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, reload, setData };
}

/** Shown on every screen that runs on synthetic data until its backend route exists. */
export function MockNotice({ children }: { children?: React.ReactNode }) {
  return (
    <p className="mb-4 flex items-start gap-2 text-xs text-subtle" data-testid="mock-notice">
      <Info aria-hidden className="mt-px size-3.5 shrink-0" />
      <span>{children ?? "Synthetic preview data. Changes stay in this browser until the backend is connected."}</span>
    </p>
  );
}

export function Loading({ error, retry, label }: { error?: string; retry?: () => void; label?: string }) {
  return <LoadState error={error || null} retry={retry} label={label ?? "Loading…"} />;
}

export const conclusionMeta: Record<Conclusion, { label: string; variant: "success" | "warning" | "danger" | "default" }> = {
  pass: { label: "Pass", variant: "success" },
  partial: { label: "Partial", variant: "warning" },
  fail: { label: "Fail", variant: "danger" },
  na: { label: "Does not apply", variant: "default" },
};
export function ConclusionBadge({ value }: { value: Conclusion | null }) {
  if (!value) return <Badge>Not tested</Badge>;
  const meta = conclusionMeta[value];
  return <Badge variant={meta.variant}>{meta.label}</Badge>;
}

const severityVariant: Record<Severity, "default" | "warning" | "danger"> = { low: "default", moderate: "warning", high: "danger", critical: "danger" };
export const SeverityBadge = ({ value }: { value: Severity }) => <Badge variant={severityVariant[value]} className="capitalize">{value}</Badge>;

const statusLabel: Record<FindingStatus, string> = { draft: "Draft", approved: "Approved", issued: "Issued, awaiting response", responded: "Response received", closed: "Closed" };
const statusVariant: Record<FindingStatus, "default" | "brand" | "deadline" | "success"> = { draft: "default", approved: "brand", issued: "deadline", responded: "brand", closed: "success" };
export const FindingStatusBadge = ({ value }: { value: FindingStatus }) => <Badge variant={statusVariant[value]}>{statusLabel[value]}</Badge>;

export const fmtDate = (iso: string | null) => (iso ? new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" }) : "—");
export const fmtDateTime = (iso: string | null) => (iso ? new Date(iso).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZone: "UTC" }) + " UTC" : "—");
export const money = (cents: number) => (cents / 100).toLocaleString("en-US", { style: "currency", currency: "USD" });
