"use client";

import { useState } from "react";
import { signOutOtherDevices, USE_MOCKS } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function SignOutOtherDevices() {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function run() {
    setBusy(true);
    setMessage("");
    setError("");
    try {
      const result = await signOutOtherDevices();
      setMessage(
        result.sessions_ended + result.devices_forgotten === 0
          ? "No other devices were signed in."
          : "Other devices are signed out and will need a new emailed code.",
      );
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Could not sign out other devices.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Signed-in devices</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4 text-sm">
        <p className="text-muted">
          After you enter an emailed code you can remember a browser for 30 days. Sign out
          every other device and forget those remembered browsers. This device stays signed in.
        </p>
        {USE_MOCKS ? (
          <p className="rounded-lg border border-warning/30 bg-warning/5 p-3 text-muted">
            Synthetic demo only. Nothing is signed out.
          </p>
        ) : null}
        <div>
          <Button type="button" variant="secondary" onClick={() => void run()} disabled={busy}>
            {busy ? "Signing out…" : "Sign out other devices"}
          </Button>
        </div>
        {message ? (
          <p role="status" className="status-note" data-tone="success">
            {message}
          </p>
        ) : null}
        {error ? (
          <p role="alert" className="status-note" data-tone="danger">
            {error}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
