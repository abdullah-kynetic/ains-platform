"use client";

import { FormEvent, Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Logo } from "@/components/brand/logo";
import { SiteFooter } from "@/components/brand/site-footer";
import { productName } from "@/lib/brand";
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
  passwordSignIn,
  requestMagicLink,
  startAuditorMFAEnrollment,
  verifyMagicLink,
  USE_MOCKS,
  type AuditorMFAEnrollment,
} from "@/lib/api";

function SignInForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { session, refresh } = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [enrollment, setEnrollment] =
    useState<AuditorMFAEnrollment | null>(null);
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);
  const token = searchParams.get("token") ?? "";
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (session)
      router.replace(session.user.role === "auditor" ? "/auditor" : "/");
  }, [router, session]);

  async function finishSignIn(action: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await action();
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Sign-in failed.");
    } finally {
      setBusy(false);
    }
  }

  function handlePassword(event: FormEvent) {
    event.preventDefault();
    void finishSignIn(() => passwordSignIn(email, password, mfaCode));
  }

  function handleToken(event: FormEvent) {
    event.preventDefault();
    void finishSignIn(() => verifyMagicLink(token, mfaCode));
  }

  async function handleMagicLink() {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await requestMagicLink(email);
      setMessage(
        "If this invited account is active, a sign-in link has been requested.",
      );
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Could not request a sign-in link.",
      );
    } finally {
      setBusy(false);
    }
  }

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
    <main id="main-content" className="flex-1 px-[var(--space-4)] py-[var(--space-8)] sm:py-[var(--space-9)]">
      <div className="mx-auto grid w-full max-w-md gap-[var(--space-6)]">
        <Logo sub="Secure portal" className="justify-self-center" />
        <Card featured>
          <CardHeader>
            <h1 className="type-title">
              {token ? "Complete sign in" : `Sign in to ${productName}`}
            </h1>
            <CardDescription>
              Invite-only access. Auditors must also enter their MFA code.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {USE_MOCKS && (
              <div className="mb-5 grid gap-3 rounded-lg border border-border p-3">
                <p className="text-sm text-muted">
                  Synthetic demo only. Do not enter real account credentials.
                </p>
                <Button
                  onClick={() => {
                    localStorage.removeItem("ains-synthetic-signed-out");
                    void refresh();
                  }}
                >
                  Open synthetic demo
                </Button>
              </div>
            )}
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
                <Button onClick={() => void refresh()}>
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
            ) : token ? (
              <form className="grid gap-4" onSubmit={handleToken}>
                <Field
                  label="Auditor MFA or recovery code (if required)"
                  htmlFor="token-mfa"
                >
                  <Input
                    id="token-mfa"
                    autoComplete="one-time-code"
                    maxLength={32}
                    value={mfaCode}
                    onChange={(event) => setMfaCode(event.target.value)}
                  />
                </Field>
                <Button type="submit" disabled={busy}>
                  {busy ? "Signing in…" : "Use secure sign-in link"}
                </Button>
              </form>
            ) : (
              <form className="grid gap-4" onSubmit={handlePassword}>
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
                <Field
                  label="Auditor MFA or recovery code (if required)"
                  htmlFor="mfa"
                >
                  <Input
                    id="mfa"
                    autoComplete="one-time-code"
                    maxLength={32}
                    value={mfaCode}
                    onChange={(event) => setMfaCode(event.target.value)}
                  />
                </Field>
                <Button type="submit" disabled={busy}>
                  {busy ? "Signing in…" : "Sign in"}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  disabled={busy || !email}
                  onClick={() => void handleMagicLink()}
                >
                  Email me a sign-in link
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  disabled={busy || !email || password.length < 8}
                  onClick={() => void startEnrollment()}
                >
                  Set up auditor MFA
                </Button>
                <a href="/reset-password" className="text-sm leading-normal text-brand underline underline-offset-4">Forgot your password?</a>
              </form>
            )}
            {message ? (
              <StatusNote tone="success" role="status" className="mt-[var(--space-4)]">
                {message}
              </StatusNote>
            ) : null}
            {error ? (
              <StatusNote tone="danger" role="alert" className="mt-[var(--space-4)]">
                {error}
              </StatusNote>
            ) : null}
          </CardContent>
        </Card>
        <p className="text-center text-xs text-subtle">
          Only invited firm users and {productName} auditors can sign in.
        </p>
      </div>
    </main>
    <SiteFooter />
    </div>
  );
}

export default function SignInPage() {
  return (
    <Suspense fallback={<LoadState label="Loading sign-in…" />}>
      <SignInForm />
    </Suspense>
  );
}
