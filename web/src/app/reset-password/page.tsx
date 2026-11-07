"use client";

import Link from "next/link";
import { Suspense, useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";
import { SiteFooter } from "@/components/brand/site-footer";
import { Logo } from "@/components/brand/logo";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Field } from "@/components/ui/label";
import { LoadState } from "@/components/ui/load-state";
import { StatusNote } from "@/components/ui/status-note";
import { apiRequest, USE_MOCKS } from "@/lib/api";

function ResetForm() {
  const token = useSearchParams().get("token") ?? "";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [complete, setComplete] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    if (USE_MOCKS) {
      setMessage("Synthetic demo only. Password recovery requires the live portal.");
      return;
    }
    if (token && password !== confirmation) {
      setError("Passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      await apiRequest(`/auth/password-reset/${token ? "confirm" : "request"}`, {
        method: "POST",
        body: JSON.stringify(token ? { token, password } : { email }),
      });
      setMessage(token ? "Password updated. Sign in with your new password." : "If an active account exists, a reset link will be emailed to you.");
      setComplete(Boolean(token));
      setPassword("");
      setConfirmation("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not reset your password. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col">
    <main id="main-content" className="flex-1 px-[var(--space-4)] py-[var(--space-8)] sm:py-[var(--space-9)]">
      <div className="mx-auto grid w-full max-w-md gap-[var(--space-6)]">
        <Logo sub="Secure portal" className="justify-self-center" />
        <Card featured>
          <CardHeader>
            <h1 className="type-title">Reset your password</h1>
          </CardHeader>
          <CardContent className="grid gap-[var(--space-4)]">
            {USE_MOCKS ? <p className="text-sm leading-normal text-muted">Synthetic demo only</p> : null}
            {!complete ? (
              <form className="grid gap-[var(--space-4)]" onSubmit={(event) => void submit(event)}>
                {token ? (
                  <>
                    <Field label="New password" htmlFor="new-password">
                      <Input id="new-password" type="password" autoComplete="new-password" required minLength={12} maxLength={1024} value={password} onChange={(event) => setPassword(event.target.value)} />
                    </Field>
                    <Field label="Confirm password" htmlFor="confirm-password">
                      <Input id="confirm-password" type="password" autoComplete="new-password" required minLength={12} maxLength={1024} value={confirmation} onChange={(event) => setConfirmation(event.target.value)} />
                    </Field>
                  </>
                ) : (
                  <Field label="Email" htmlFor="reset-email">
                    <Input id="reset-email" type="email" autoComplete="email" required maxLength={320} value={email} onChange={(event) => setEmail(event.target.value)} />
                  </Field>
                )}
                <Button type="submit" disabled={busy}>{busy ? "Sending…" : token ? "Set new password" : "Email reset link"}</Button>
              </form>
            ) : null}
            {error ? <StatusNote tone="danger" role="alert">{error}</StatusNote> : null}
            {message ? <StatusNote tone="info" role="status">{message}</StatusNote> : null}
            <Link className="inline-flex min-h-[var(--control-height)] items-center text-sm text-brand underline underline-offset-4" href="/sign-in">Back to sign in</Link>
          </CardContent>
        </Card>
      </div>
    </main>
    <SiteFooter />
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<LoadState label="Loading password recovery…" />}>
      <ResetForm />
    </Suspense>
  );
}
