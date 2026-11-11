"use client";

import { FormEvent, Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Logo } from "@/components/brand/logo";
import { SiteFooter } from "@/components/brand/site-footer";
import { productName } from "@/lib/brand";
import { LoadState } from "@/components/ui/load-state";
import { useSession } from "@/components/auth/session";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Field } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { StatusNote } from "@/components/ui/status-note";
import {
  ApiError,
  EMAIL_CODE_REQUIRED,
  passwordSignIn,
  resendEmailCode,
  verifyMagicLink,
} from "@/lib/api";
import { sanitizeSignInNext } from "@/lib/sign-in-next";
import { signInErrorText } from "@/lib/sign-in-message";

function SignInForm() {
  const router = useRouter();
  const params = useSearchParams();
  const { session, refresh } = useSession();
  const next = sanitizeSignInNext(params.get("next"));
  const token = params.get("token");
  const [step, setStep] = useState<"credentials" | "code">("credentials");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [remember, setRemember] = useState(false);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (session) router.replace(next);
  }, [session, router, next]);

  async function authenticate() {
    setBusy(true);
    setError("");
    try {
      if (token) await verifyMagicLink(token);
      else await passwordSignIn(email.trim(), password, code, remember);
      await refresh();
      router.replace(next);
    } catch (caught) {
      if (
        caught instanceof ApiError &&
        caught.status === 401 &&
        caught.message === EMAIL_CODE_REQUIRED
      ) {
        setCode("");
        setNotice(`We emailed a 6-digit code to ${email.trim()}. It expires in 10 minutes.`);
        setStep("code");
      } else if (caught instanceof ApiError) {
        setError(
          signInErrorText(
            { status: caught.status, message: caught.message, retryAfterSeconds: caught.retryAfterSeconds },
            step,
          ),
        );
      } else {
        setError("Sign-in could not be completed. Try again.");
      }
    } finally {
      setBusy(false);
    }
  }

  async function resend() {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await resendEmailCode(email.trim(), password);
      setCode("");
      setNotice("We sent a new code. The earlier one no longer works.");
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? signInErrorText(
              { status: caught.status, message: caught.message, retryAfterSeconds: caught.retryAfterSeconds },
              "credentials",
            ).replace("Email or password is incorrect", "Could not send a new code. Try again.")
          : "Could not send a new code. Try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    void authenticate();
  }

  return (
    <div className="flex min-h-screen flex-col">
      <main
        id="main-content"
        className="flex-1 px-[var(--space-4)] py-[var(--space-8)] sm:py-[var(--space-9)]"
      >
        <div className="mx-auto grid w-full max-w-md gap-[var(--space-6)]">
          <Logo sub="Secure portal" className="justify-self-center" />
          <Card featured>
            <CardHeader>
              <h1 className="type-title">Sign in to {productName}</h1>
            </CardHeader>
            <CardContent>
              <form className="grid gap-4" onSubmit={submit}>
                {step === "credentials" && !token ? (
                  <>
                    <Field label="Email" htmlFor="email">
                      <Input
                        id="email"
                        type="email"
                        autoComplete="email"
                        required
                        autoFocus
                        value={email}
                        onChange={(event) => setEmail(event.target.value)}
                      />
                    </Field>
                    <Field label="Password" htmlFor="password">
                      <Input
                        key="password"
                        id="password"
                        type="password"
                        autoComplete="current-password"
                        required
                        maxLength={1024}
                        value={password}
                        onChange={(event) => setPassword(event.target.value)}
                      />
                    </Field>
                  </>
                ) : step === "code" ? (
                  <>
                    {notice ? (
                      <StatusNote tone="info" role="status">
                        {notice}
                      </StatusNote>
                    ) : null}
                    <Field label="6-digit code from your email" htmlFor="email-code">
                      <Input
                        key="email-code"
                        id="email-code"
                        inputMode="numeric"
                        autoComplete="one-time-code"
                        required
                        minLength={6}
                        maxLength={12}
                        autoFocus
                        value={code}
                        onChange={(event) => setCode(event.target.value)}
                      />
                    </Field>
                    <label className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        className="size-5 accent-brand"
                        checked={remember}
                        onChange={(event) => setRemember(event.target.checked)}
                      />
                      Remember this browser for 30 days
                    </label>
                  </>
                ) : null}
                <Button type="submit" disabled={busy}>
                  {busy ? "Signing in…" : step === "code" ? "Verify" : "Sign in"}
                </Button>
                {step === "code" ? (
                  <Button
                    type="button"
                    variant="ghost"
                    disabled={busy}
                    onClick={() => void resend()}
                  >
                    Send a new code
                  </Button>
                ) : null}
                {step === "credentials" && !token ? (
                  <a
                    href="/reset-password"
                    className="text-sm leading-normal text-brand underline underline-offset-4"
                  >
                    Forgot password?
                  </a>
                ) : null}
              </form>
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

export default function SignInPage() {
  return (
    <Suspense fallback={<LoadState label="Loading sign-in…" />}>
      <SignInForm />
    </Suspense>
  );
}
