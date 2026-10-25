"use client";

import { useState, type FormEvent } from "react";
import { rotateAuditorMFARecoveryCodes, USE_MOCKS } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Field } from "@/components/ui/label";

export function MFARecoveryCodes() {
  const [code, setCode] = useState("");
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function rotate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      setRecoveryCodes(await rotateAuditorMFARecoveryCodes(code));
      setCode("");
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Could not replace recovery codes.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Auditor MFA recovery</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4 text-sm">
        <p className="text-muted">
          Replace all unused recovery codes after confirming a current
          authenticator code. Each recovery code works once.
        </p>
        {USE_MOCKS ? (
          <p className="rounded-lg border border-warning/30 bg-warning/5 p-3 text-muted">
            Synthetic demo only. Use code 123456; generated values are not real
            credentials.
          </p>
        ) : null}
        <form className="flex flex-wrap items-end gap-3" onSubmit={rotate}>
          <Field label="Current authenticator code" htmlFor="rotate-mfa-code">
            <Input
              id="rotate-mfa-code"
              inputMode="numeric"
              autoComplete="one-time-code"
              minLength={6}
              maxLength={8}
              required
              value={code}
              onChange={(event) => setCode(event.target.value)}
            />
          </Field>
          <Button type="submit" disabled={busy || code.length < 6}>
            {busy ? "Replacing…" : "Replace recovery codes"}
          </Button>
        </form>
        {error ? (
          <p role="alert" className="status-note" data-tone="danger">
            {error}
          </p>
        ) : null}
        {recoveryCodes.length ? (
          <div role="status" className="rounded-lg border border-warning/30 p-4">
            <p className="font-medium">Save these codes now</p>
            <p className="mt-1 text-muted">
              Previous unused codes are revoked. These values will not be shown
              again.
            </p>
            <ul className="mt-3 grid gap-1 font-mono text-xs sm:grid-cols-2">
              {recoveryCodes.map((recoveryCode) => (
                <li key={recoveryCode}>{recoveryCode}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
