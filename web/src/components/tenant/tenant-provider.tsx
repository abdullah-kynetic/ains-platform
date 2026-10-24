"use client";

import { createContext, useContext, useMemo } from "react";
import type { TenantBranding } from "@/lib/tenant";

export type TenantValue = {
  slug: string;
  branding: TenantBranding;
};

const TenantContext = createContext<TenantValue | null>(null);

export function TenantProvider({
  slug,
  branding,
  children,
}: TenantValue & { children: React.ReactNode }) {
  const value = useMemo(() => ({ slug, branding }), [slug, branding]);
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
