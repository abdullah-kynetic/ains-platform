"use client";

import { FormEvent, Suspense, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Logo } from "@/components/brand/logo";
import { SiteFooter } from "@/components/brand/site-footer";
import { LoadState } from "@/components/ui/load-state";
import { useSession } from "@/components/auth/session";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
} from "@/components/ui/card";
import { Field } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { StatusNote } from "@/components/ui/status-note";
import {
  confirmAuditorMFAEnrollment,
  startAuditorMFAEnrollment,
  USE_MOCKS,
  type AuditorMFAEnrollment,
} from "@/lib/api";

function AccountSetupForm() {
  const router = useRouter();
  const { session, refresh } = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [enrollment, setEnrollment] = useState<AuditorMFAEnrollment | null>(
    null,
  );
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);

  const [busy, setBusy] = useState(false);

  const [error, setError] = useState("");

  useEffect(() => {
    if (session && !recoveryCodes.length)
      router.replace(session.user.role === "auditor" ? "/auditor" : "/");
  }, [router, session, recoveryCodes.length]);

  async function startEnrollment() {
    setBusy(true);
    setError("");
    try {
      setEnrollment(await startAuditorMFAEnrollment(email, password));
      setMfaCode("");
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Could not start MFA enrollment.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function confirmEnrollment(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const completed = await confirmAuditorMFAEnrollment(
        email,
        password,
        mfaCode,
      );
      setRecoveryCodes(completed.recovery_codes);
      setEnrollment(null);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Could not confirm MFA enrollment.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-glow">
      <main
        id="main-content"
        className="flex-1 px-[var(--space-4)] py-[var(--space-8)] sm:py-[var(--space-9)]"
      >
        <div className="mx-auto grid w-full max-w-md gap-[var(--space-6)]">
          <Logo sub="Secure portal" className="justify-self-center" />
          <Card featured>
            <CardHeader>
              <h1 className="type-title">Set up auditor MFA</h1>
              <CardDescription>
                Enroll your authenticator to finish account setup.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {recoveryCodes.length ? (
                <div className="grid gap-4">
                  <p className="rounded-lg border border-warning/30 bg-warning/5 p-3 text-sm text-muted">
                    Save these recovery codes now. Each works once and they will
                    not be shown again.
                  </p>
                  <ul className="grid gap-1 font-mono text-xs sm:grid-cols-2">
                    {recoveryCodes.map((code) => (
                      <li key={code}>{code}</li>
                    ))}
                  </ul>
                  <Button
                    onClick={() => {
                      void refresh().then(() => router.replace("/auditor"));
                    }}
                  >
                    I saved my recovery codes
                  </Button>
                </div>
              ) : enrollment ? (
                <form className="grid gap-4" onSubmit={confirmEnrollment}>
                  {USE_MOCKS ? (
                    <p className="rounded-lg border border-warning/30 bg-warning/5 p-3 text-sm text-muted">
                      Synthetic demo only. Use authenticator code 123456.
                    </p>
                  ) : null}
                  <p className="text-sm text-muted">
                    Add this setup key to your authenticator app, then enter its
                    current six-digit code. Enrollment expires at{" "}
                    {new Date(enrollment.expires_at).toLocaleTimeString()}.
                  </p>
                  <div className="break-all rounded-lg border border-border p-3 font-mono text-sm">
                    {enrollment.secret}
                  </div>
                  <Field label="Authenticator code" htmlFor="enrollment-code">
                    <Input
                      id="enrollment-code"
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      minLength={6}
                      maxLength={8}
                      required
                      value={mfaCode}
                      onChange={(event) => setMfaCode(event.target.value)}
                    />
                  </Field>
                  <Button type="submit" disabled={busy || mfaCode.length < 6}>
                    {busy ? "Confirming…" : "Confirm and enable MFA"}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    disabled={busy}
                    onClick={() => setEnrollment(null)}
                  >
                    Cancel enrollment
                  </Button>
                </form>
              ) : (
                <form
                  className="grid gap-4"
                  onSubmit={(event) => {
                    event.preventDefault();
                    void startEnrollment();
                  }}
                >
                  <Field label="Email" htmlFor="email">
                    <Input
                      id="email"
                      type="email"
                      autoComplete="email"
                      required
                      value={email}
                      onChange={(event) => setEmail(event.target.value)}
                    />
                  </Field>
                  <Field label="Password" htmlFor="password">
                    <Input
                      id="password"
                      type="password"
                      autoComplete="current-password"
                      minLength={8}
                      required
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                    />
                  </Field>
                  <Button
                    type="submit"
                    disabled={busy || !email || password.length < 8}
                  >
                    Set up auditor MFA
                  </Button>
                </form>
              )}
              {error ? (
                <StatusNote
                  tone="danger"
                  role="alert"
                  className="mt-[var(--space-4)]"
                >
                  {error}
                </StatusNote>
              ) : null}
            </CardContent>
          </Card>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}

export default function AccountSetupPage() {
  return (
    <Suspense fallback={<LoadState label="Loading account setup…" />}>
      <AccountSetupForm />
    </Suspense>
  );
}
