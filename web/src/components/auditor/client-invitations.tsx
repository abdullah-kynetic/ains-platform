"use client";

import { useEffect, useState, type FormEvent } from "react";
import { InvitationEmailPreview } from "@/components/brand/email-preview";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Field } from "@/components/ui/label";
import {
  createClientInvitation,
  getClientInvitations,
  resendClientInvitation,
  revokeClientInvitation,
  type ClientInvitation,
} from "@/lib/api";

function replaceInvitation(
  invitations: ClientInvitation[],
  updated: ClientInvitation,
) {
  const found = invitations.some((entry) => entry.id === updated.id);
  return found
    ? invitations.map((entry) => (entry.id === updated.id ? updated : entry))
    : [updated, ...invitations];
}

export function ClientInvitations({
  engagementId,
  firmId,
  firmName,
}: {
  engagementId: string;
  firmId?: string;
  firmName: string;
}) {
  const [invitations, setInvitations] = useState<ClientInvitation[] | null>(
    null,
  );
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [preview, setPreview] = useState<ClientInvitation | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    getClientInvitations(engagementId)
      .then(setInvitations)
      .catch((reason: unknown) =>
        setError(
          reason instanceof Error
            ? reason.message
            : "Could not load client invitations.",
        ),
      );
  }, [engagementId]);

  async function run(action: () => Promise<ClientInvitation>, message: string) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const updated = await action();
      setInvitations((current) => replaceInvitation(current ?? [], updated));
      setPreview(updated.previewPath ? updated : null);
      setNotice(message);
      return updated;
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Could not update this invitation.",
      );
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function invite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const created = await run(
      () =>
        createClientInvitation(
          engagementId,
          firmId ?? `synthetic-firm-${engagementId}`,
          firmName,
          { email, name },
        ),
      "Invitation created. No email was sent; local preview appears only when explicitly enabled.",
    );
    if (created) {
      setEmail("");
      setName("");
    }
  }

  return (
    <section
      aria-labelledby={`client-invitations-${engagementId}`}
      className="grid gap-4 rounded-xl border border-border bg-elevated/40 p-4"
    >
      <div>
        <h2
          id={`client-invitations-${engagementId}`}
          className="font-semibold"
        >
          Client access
        </h2>
        <p className="mt-1 text-sm text-muted">
          Invitations expire, work once, and create a client account bound only
          to {firmName}.
        </p>
      </div>

      <form className="grid gap-4 sm:grid-cols-2" onSubmit={invite}>
        <Field label="Client name" htmlFor={`invite-name-${engagementId}`}>
          <Input
            id={`invite-name-${engagementId}`}
            value={name}
            onChange={(event) => setName(event.target.value)}
            minLength={1}
            maxLength={255}
            required
          />
        </Field>
        <Field label="Client email" htmlFor={`invite-email-${engagementId}`}>
          <Input
            id={`invite-email-${engagementId}`}
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            maxLength={320}
            required
          />
        </Field>
        <div className="sm:col-span-2">
          <Button type="submit" disabled={busy || !name.trim() || !email.trim()}>
            {busy ? "Creating…" : "Create invitation"}
          </Button>
        </div>
      </form>

      {preview?.previewPath ? (
        <div className="grid gap-3">
          <div className="rounded-lg border border-warning/30 bg-warning/5 p-3 text-sm">
            <p className="font-medium text-foreground">
              Synthetic local invitation preview
            </p>
            <p className="mt-1 text-muted">
              This one-time link is shown only because local preview mode is
              enabled. Never use it for a real client or expose it in logs.
            </p>
          </div>
          <InvitationEmailPreview
            to={preview.email}
            firmName={preview.firmName}
            previewPath={preview.previewPath}
            expiresAt={preview.expiresAt}
          />
        </div>
      ) : null}

      {notice ? (
        <p role="status" className="status-note" data-tone="success">
          {notice}
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="status-note" data-tone="danger">
          {error}
        </p>
      ) : null}

      {invitations?.length ? (
        <ul className="grid gap-3">
          {invitations.map((invitation) => (
            <li
              key={invitation.id}
              className="grid gap-3 rounded-lg border border-border bg-surface p-3 sm:grid-cols-[1fr_auto] sm:items-center"
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-medium">{invitation.name}</p>
                  <Badge
                    variant={
                      invitation.status === "pending"
                        ? "warning"
                        : invitation.status === "accepted"
                          ? "success"
                          : "danger"
                    }
                  >
                    {invitation.status}
                  </Badge>
                </div>
                <p className="break-all text-sm text-muted">
                  {invitation.email}
                </p>
                <p className="mt-1 text-xs text-subtle">
                  Expires {new Date(invitation.expiresAt).toLocaleString()}
                </p>
              </div>
              {invitation.status !== "accepted" ? (
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={busy}
                    onClick={() =>
                      void run(
                        () => resendClientInvitation(invitation.id),
                        "Invitation reissued. The previous link no longer works, and no email was sent.",
                      )
                    }
                  >
                    Resend invitation
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="destructive"
                    disabled={busy || invitation.status === "revoked"}
                    onClick={() =>
                      void run(
                        () => revokeClientInvitation(invitation.id),
                        "Invitation revoked.",
                      )
                    }
                  >
                    Revoke invitation
                  </Button>
                </div>
              ) : null}
            </li>
          ))}
        </ul>
      ) : invitations ? (
        <p className="text-sm text-muted">No client invitation has been created.</p>
      ) : (
        <p className="text-sm text-muted">Loading client invitations…</p>
      )}
    </section>
  );
}
