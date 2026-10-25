"use client";

import { Suspense, useEffect, useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Logo } from "@/components/brand/logo";
import { SiteFooter } from "@/components/brand/site-footer";
import { useSession } from "@/components/auth/session";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Field } from "@/components/ui/label";
import { LoadState } from "@/components/ui/load-state";
import {
  acceptClientInvitation,
  getInvitationDetails,
  USE_MOCKS,
  type InvitationDetails,
} from "@/lib/api";

function AcceptInvitationForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const { refresh } = useSession();
  const [invitation, setInvitation] = useState<InvitationDetails | null>(null);
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    getInvitationDetails(token)
      .then(setInvitation)
      .catch((reason: unknown) =>
        setError(
          reason instanceof Error
            ? reason.message
            : "This invitation is unavailable.",
        ),
      )
      .finally(() => setLoading(false));
  }, [token]);

  const visibleError = token ? error : "This invitation link is incomplete.";

  async function accept(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (password !== confirmation) {
      setError("Passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      await acceptClientInvitation(token, password);
      await refresh();
      router.replace("/");
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Could not accept this invitation.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col page-enter">
    <main id="main-content" className="flex-1 px-[var(--space-4)] py-[var(--space-8)] sm:py-[var(--space-9)]">
      <div className="mx-auto grid w-full max-w-md gap-[var(--space-6)]">
        <Logo sub="Secure client access" className="justify-self-center" />
        <Card featured>
          <CardHeader>
            <h1 className="type-title">Accept client invitation</h1>
            <CardDescription>
              Create your password to activate access to this firm’s isolated
              workspace.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {token && loading ? <LoadState label="Checking invitation…" /> : null}
            {invitation ? (
              <form className="grid gap-4" onSubmit={accept}>
                {USE_MOCKS ? (
                  <p className="rounded-lg border border-warning/30 bg-warning/5 p-3 text-sm text-muted">
                    Synthetic demo only. Do not enter a real password or client
                    identity.
                  </p>
                ) : null}
                <div className="rounded-lg border border-border p-3 text-sm">
                  <p className="font-medium">{invitation.firmName}</p>
                  <p className="mt-1 text-muted">
                    {invitation.name} · {invitation.email}
                  </p>
                  <p className="mt-1 text-xs text-subtle">
                    Expires {new Date(invitation.expiresAt).toLocaleString()}
                  </p>
                </div>
                <Field label="Create password" htmlFor="invitation-password">
                  <Input
                    id="invitation-password"
                    type="password"
                    autoComplete="new-password"
                    minLength={12}
                    maxLength={1024}
                    required
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                  />
                </Field>
                <Field label="Confirm password" htmlFor="invitation-confirmation">
                  <Input
                    id="invitation-confirmation"
                    type="password"
                    autoComplete="new-password"
                    minLength={12}
                    maxLength={1024}
                    required
                    value={confirmation}
                    onChange={(event) => setConfirmation(event.target.value)}
                  />
                </Field>
                <Button
                  type="submit"
                  disabled={busy || password.length < 12 || !confirmation}
                >
                  {busy ? "Activating…" : "Set password and activate account"}
                </Button>
              </form>
            ) : null}
            {visibleError ? (
              <p className="status-note mt-[var(--space-4)]" data-tone="danger" role="alert">
                {visibleError}
              </p>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </main>
    <SiteFooter />
    </div>
  );
}

export default function AcceptInvitationPage() {
  return (
    <Suspense fallback={<LoadState label="Loading invitation…" />}>
      <AcceptInvitationForm />
    </Suspense>
  );
}
