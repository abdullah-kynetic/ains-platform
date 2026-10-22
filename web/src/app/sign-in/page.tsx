"use client";

import { FormEvent, Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Logo } from "@/components/brand/logo";
import { useSession } from "@/components/auth/session";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { passwordSignIn, requestMagicLink, verifyMagicLink } from "@/lib/api";

function SignInForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { session, refresh } = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const token = searchParams.get("token") ?? "";
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (session) router.replace(session.user.role === "auditor" ? "/auditor" : "/");
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
      setMessage("If this invited account is active, a sign-in link has been requested.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not request a sign-in link.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen bg-glow px-4 py-12">
      <div className="mx-auto grid w-full max-w-md gap-7">
        <Logo sub="Secure portal" className="justify-self-center" />
        <Card featured>
          <CardHeader>
            <CardTitle>{token ? "Complete sign in" : "Sign in to AINS"}</CardTitle>
            <CardDescription>
              Invite-only access. Auditors must also enter their MFA code.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {token ? (
              <form className="grid gap-4" onSubmit={handleToken}>
                <Field label="Auditor MFA code (if required)" htmlFor="token-mfa">
                  <Input id="token-mfa" inputMode="numeric" autoComplete="one-time-code" value={mfaCode} onChange={(event) => setMfaCode(event.target.value)} />
                </Field>
                <Button type="submit" disabled={busy}>{busy ? "Signing in…" : "Use secure sign-in link"}</Button>
              </form>
            ) : (
              <form className="grid gap-4" onSubmit={handlePassword}>
                <Field label="Email" htmlFor="email">
                  <Input id="email" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
                </Field>
                <Field label="Password" htmlFor="password">
                  <Input id="password" type="password" autoComplete="current-password" minLength={8} required value={password} onChange={(event) => setPassword(event.target.value)} />
                </Field>
                <Field label="Auditor MFA code (if required)" htmlFor="mfa">
                  <Input id="mfa" inputMode="numeric" autoComplete="one-time-code" value={mfaCode} onChange={(event) => setMfaCode(event.target.value)} />
                </Field>
                <Button type="submit" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</Button>
                <Button type="button" variant="outline" disabled={busy || !email} onClick={() => void handleMagicLink()}>Email me a sign-in link</Button>
              </form>
            )}
            {message ? <p className="mt-4 text-sm text-green-400" role="status">{message}</p> : null}
            {error ? <p className="mt-4 text-sm text-red-400" role="alert">{error}</p> : null}
          </CardContent>
        </Card>
        <p className="text-center text-xs text-subtle">Only invited firm users and AINS auditors can sign in.</p>
      </div>
    </main>
  );
}

export default function SignInPage() {
  return <Suspense><SignInForm /></Suspense>;
}
