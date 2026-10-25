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
import { ApiError, passwordSignIn, verifyMagicLink } from "@/lib/api";
import { sanitizeSignInNext } from "@/lib/sign-in-next";

function SignInForm() {
  const router = useRouter();
  const params = useSearchParams();
  const { session, refresh } = useSession();
  const next = sanitizeSignInNext(params.get("next"));
  const token = params.get("token");
  const [step, setStep] = useState<"credentials" | "mfa">("credentials");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (session) router.replace(next);
  }, [session, router, next]);

  async function authenticate() {
    setBusy(true);
    setError("");
    try {
      if (token) await verifyMagicLink(token, code);
      else await passwordSignIn(email.trim(), password, code);
      await refresh();
      router.replace(next);
    } catch (caught) {
      if (
        caught instanceof ApiError &&
        caught.status === 401 &&
        caught.message === "MFA code required"
      ) {
        setStep("mfa");
      } else if (
        caught instanceof ApiError &&
        caught.status === 403 &&
        caught.message === "Auditor MFA enrollment is required"
      ) {
        router.push("/account-setup");
      } else {
        setError("Email or password is incorrect");
      }
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
    <div className="flex min-h-screen flex-col bg-glow">
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
                ) : step === "mfa" ? (
                  <Field label="Authenticator or recovery code" htmlFor="mfa">
                    <Input
                      key="mfa"
                      id="mfa"
                      autoComplete="one-time-code"
                      required
                      minLength={6}
                      maxLength={32}
                      autoFocus
                      value={code}
                      onChange={(event) => setCode(event.target.value)}
                    />
                  </Field>
                ) : null}
                <Button type="submit" disabled={busy}>
                  {busy ? "Signing in…" : step === "mfa" ? "Verify" : "Sign in"}
                </Button>
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
