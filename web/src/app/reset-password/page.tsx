"use client";

import Link from "next/link";
import { Suspense, useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Field } from "@/components/ui/label";
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
    <main id="main-content" className="min-h-screen bg-glow px-4 py-12">
      <div className="mx-auto grid w-full max-w-md gap-6 rounded-xl border border-line bg-surface p-6">
        <h1 className="text-xl font-semibold">Reset your password</h1>
        {USE_MOCKS ? <p>Synthetic demo only</p> : null}
        {!complete ? <form className="grid gap-4" onSubmit={(event) => void submit(event)}>
          {token ? <>
            <Field label="New password" htmlFor="new-password">
              <Input id="new-password" type="password" autoComplete="new-password" required minLength={12} maxLength={1024} value={password} onChange={(event) => setPassword(event.target.value)} />
            </Field>
            <Field label="Confirm password" htmlFor="confirm-password">
              <Input id="confirm-password" type="password" autoComplete="new-password" required minLength={12} maxLength={1024} value={confirmation} onChange={(event) => setConfirmation(event.target.value)} />
            </Field>
          </> : <Field label="Email" htmlFor="reset-email">
            <Input id="reset-email" type="email" autoComplete="email" required maxLength={320} value={email} onChange={(event) => setEmail(event.target.value)} />
          </Field>}
          <Button type="submit" disabled={busy}>{busy ? "Sending…" : token ? "Set new password" : "Email reset link"}</Button>
        </form> : null}
        {error ? <p role="alert">{error}</p> : null}
        {message ? <p role="status">{message}</p> : null}
        <Link className="underline" href="/sign-in">Back to sign in</Link>
      </div>
    </main>
  );
}

export default function ResetPasswordPage() {
  return <Suspense fallback={<main id="main-content">Loading password recovery…</main>}><ResetForm /></Suspense>;
}
