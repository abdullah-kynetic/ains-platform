"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { getSession, signOut, type SessionData, type UserRole } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";

type SessionContextValue = {
  session: SessionData | null;
  loading: boolean;
  refresh: () => Promise<void>;
  logOut: () => Promise<void>;
};

const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<SessionData | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setSession(await getSession());
    } catch {
      setSession(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    getSession().then(setSession).catch(() => setSession(null)).finally(() => setLoading(false));
  }, []);

  const logOut = useCallback(async () => {
    await signOut();
    setSession(null);
  }, []);

  const value = useMemo<SessionContextValue>(
    () => ({
      session,
      loading,
      refresh,
      logOut,
    }),
    [session, loading, refresh, logOut],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const context = useContext(SessionContext);
  if (!context) throw new Error("useSession must be used inside SessionProvider");
  return context;
}

export function AuthGate({ children, role }: { children: React.ReactNode; role?: UserRole }) {
  const { session, loading } = useSession();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (loading) return;
    if (!session) {
      router.replace(`/sign-in?next=${encodeURIComponent(pathname)}`);
    } else if (role && session.user.role !== role) {
      router.replace(session.user.role === "auditor" ? "/auditor" : "/");
    }
  }, [loading, pathname, role, router, session]);

  if (loading || !session || (role && session.user.role !== role)) {
    return (
      <div className="mx-auto mt-24 w-full max-w-xl px-4">
        <Skeleton className="h-36 w-full" />
      </div>
    );
  }
  return children;
}
