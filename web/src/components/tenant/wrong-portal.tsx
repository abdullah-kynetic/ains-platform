"use client";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
} from "@/components/ui/card";

export function WrongPortal({
  busy,
  error,
  onSignOut,
}: {
  busy: boolean;
  error: string;
  onSignOut: () => void;
}) {
  return (
    <main
      id="main-content"
      data-tenant-state="wrong-portal"
      className="min-h-screen page-enter px-4 py-16"
    >
      <div className="mx-auto grid w-full max-w-lg gap-6">
        <p className="text-center text-sm font-semibold tracking-[-0.02em]">
          Kien
        </p>
        <Card featured>
          <CardHeader>
            <h1 className="text-xl font-semibold">Wrong portal</h1>
            <CardDescription>
              This sign-in belongs to a different firm. This browser can stay
              signed in to one firm at a time.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            <p className="text-sm text-muted">
              Sign out, then open the portal link for your firm.
            </p>
            <Button onClick={onSignOut} disabled={busy}>
              {busy ? "Signing out…" : "Sign out"}
            </Button>
            {error ? (
              <p className="text-sm text-red-400" role="alert">
                {error}
              </p>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
