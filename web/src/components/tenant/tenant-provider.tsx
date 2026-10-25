"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { clientMocksEnabled } from "@/lib/api";
import { fetchTenantBranding } from "@/lib/tenant-branding";
import { safeHostLabel, type TenantBranding } from "@/lib/tenant";
import { UnknownFirm } from "@/components/tenant/unknown-firm";

export type TenantValue = {
  slug: string;
  branding: TenantBranding;
};

const TenantContext = createContext<TenantValue | null>(null);

export function TenantProvider({
  slug,
  branding: initialBranding,
  children,
}: TenantValue & { children: React.ReactNode }) {
  const [branding, setBranding] = useState(initialBranding);
  const [unknown, setUnknown] = useState(false);
  const value = useMemo(() => ({ slug, branding }), [slug, branding]);

  useEffect(() => {
    if (clientMocksEnabled()) return;
    let cancelled = false;
    fetchTenantBranding().then((result) => {
      if (cancelled) return;
      if (result.status === "unknown") setUnknown(true);
      else if (result.status === "ok") setBranding(result.branding);
    });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  if (unknown) {
    return (
      <UnknownFirm
        reason="unlisted"
        host={safeHostLabel(window.location.host)}
      />
    );
  }

  return (
    <TenantContext.Provider value={value}>{children}</TenantContext.Provider>
  );
}

/** Firm slug and branding for the host that served this page. */
export function useTenant(): TenantValue {
  const value = useContext(TenantContext);
  if (!value) throw new Error("useTenant must be used inside TenantProvider");
  return value;
}
