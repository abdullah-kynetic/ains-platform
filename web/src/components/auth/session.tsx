"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  getSession,
  isWrongPortalStatus,
  onWrongPortal,
  signOut,
  clientMocksEnabled,
  ApiError,
  type SessionData,
  type SessionUser,
  type UserRole,
} from "@/lib/api";
import { audienceRefusesRole, currentAudience } from "@/lib/audience";
import { WrongPortal } from "@/components/tenant/wrong-portal";
import { LoadState } from "@/components/ui/load-state";

type SessionContextValue = {
  session: SessionData | null;
  loading: boolean;
  refresh: () => Promise<void>;
  logOut: () => Promise<void>;
  finishOnboarding: (
    userId: string,
    state: NonNullable<SessionUser["onboarding_state"]>,
  ) => void;
};

const SessionContext = createContext<SessionContextValue | null>(null);

/** A real session whose role does not belong on this host is refused, like a wrong-firm session. */
function refusedOnThisHost(next: SessionData): boolean {
  return !clientMocksEnabled() && audienceRefusesRole(currentAudience(), next.user.role);
}

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [session, setSession] = useState<SessionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [wrongPortal, setWrongPortal] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [signOutError, setSignOutError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const next = await getSession();
      if (refusedOnThisHost(next)) {
        setSession(null);
        setWrongPortal(true);
      } else {
        setSession(next);
        setWrongPortal(false);
      }
    } catch (caught) {
      setSession(null);
      if (caught instanceof ApiError && isWrongPortalStatus(caught.status, caught.message)) {
        setWrongPortal(true);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => onWrongPortal(() => setWrongPortal(true)), []);

  useEffect(() => {
    getSession()
      .then((next) => {
        if (refusedOnThisHost(next)) {
          setSession(null);
          setWrongPortal(true);
        } else {
          setSession(next);
          setWrongPortal(false);
        }
      })
      .catch((caught: unknown) => {
        setSession(null);
        if (caught instanceof ApiError && isWrongPortalStatus(caught.status, caught.message)) {
          setWrongPortal(true);
        }
      })
      .finally(() => setLoading(false));
  }, []);

  const logOut = useCallback(async () => {
    await signOut();
    setSession(null);
    setWrongPortal(false);
  }, []);

  const finishOnboarding = useCallback(
    (userId: string, state: NonNullable<SessionUser["onboarding_state"]>) => {
      setSession((current) =>
        current?.user.id === userId
          ? { ...current, user: { ...current.user, onboarding_state: state } }
          : current,
      );
    },
    [],
  );

  async function signOutOfWrongPortal() {
    setSigningOut(true);
    setSignOutError("");
    try {
      await signOut();
      setSession(null);
      setWrongPortal(false);
      router.replace("/sign-in");
    } catch {
      setSignOutError(
        "Sign-out could not be completed from this portal. Open your firm's address and sign out there.",
      );
    } finally {
      setSigningOut(false);
    }
  }

  const value = useMemo<SessionContextValue>(
    () => ({
      session,
      loading,
      refresh,
      logOut,
      finishOnboarding,
    }),
    [session, loading, refresh, logOut, finishOnboarding],
  );

  if (wrongPortal) {
    return (
      <WrongPortal
        busy={signingOut}
        error={signOutError}
        onSignOut={() => void signOutOfWrongPortal()}
      />
    );
  }

  return (
    <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
  );
}

export function useSession() {
  const context = useContext(SessionContext);
  if (!context)
    throw new Error("useSession must be used inside SessionProvider");
  return context;
}

export function AuthGate({
  children,
  role,
}: {
  children: React.ReactNode;
  role?: UserRole;
}) {
  const { session, loading } = useSession();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (loading) return;
    if (!session) {
      router.replace(`/sign-in?next=${encodeURIComponent(pathname + window.location.search + window.location.hash)}`);
    } else if (role && session.user.role !== role) {
      router.replace(session.user.role === "auditor" ? "/auditor" : "/");
    }
  }, [loading, pathname, role, router, session]);

  if (loading || !session || (role && session.user.role !== role)) {
    return (
      <div className="mx-auto mt-24 w-full max-w-xl px-4">
        <LoadState label="Checking your session…" />
      </div>
    );
  }
  return children;
}
