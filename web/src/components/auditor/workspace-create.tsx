"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Building2, CheckCircle2 } from "lucide-react";
import { AuthGate } from "@/components/auth/session";
import { ClientInvitations } from "@/components/auditor/client-invitations";
import { PageHeader } from "@/components/shell/page";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Field } from "@/components/ui/label";
import { createClientWorkspace, type CreatedWorkspace } from "@/lib/workflow-api";

export function WorkspaceCreate() {
  const router = useRouter();
  const [firmName, setFirmName] = useState("");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [created, setCreated] = useState<CreatedWorkspace | null>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSaving(true);
    try {
      setCreated(await createClientWorkspace({ firmName: firmName.trim(), reviewPeriodStart: periodStart, reviewPeriodEnd: periodEnd, dueDate: dueDate || null }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to create this workspace.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <AuthGate role="auditor">
      <PageHeader title="Add client workspace" description="Create an isolated firm and its first FINRA Rule 3310 engagement. Client access is provisioned separately." />
      <div className="max-w-2xl">
        {created ? (
          <Card>
            <CardHeader>
              <CheckCircle2 className="mb-2 size-7 text-success-foreground" aria-hidden="true" />
              <CardTitle>{created.firmName} is ready</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 text-sm text-muted">
              <p>The isolated workspace and all {created.requestCount} canonical requests were created and assigned to you.</p>
              <p className="rounded-lg border border-warning/20 bg-warning/5 px-3 py-2 text-xs">No client login exists yet. Create a single-use invitation below when the workspace is ready for client access.</p>
              <ClientInvitations engagementId={created.id} firmId={created.firmId} firmName={created.firmName} />
              <div><Button onClick={() => setCreated(null)} variant="outline">Add another workspace</Button> <Link href="/auditor" className="ml-3 text-sm font-medium text-brand-hover hover:underline">Return to review queue</Link></div>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardHeader>
              <Building2 className="mb-2 size-6 text-brand" aria-hidden="true" />
              <CardTitle>Workspace details</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={submit} className="grid gap-5">
                <Field label="Firm name" htmlFor="firm-name" hint="Use the legal or operating name for this client workspace.">
                  <Input id="firm-name" value={firmName} onChange={(event) => setFirmName(event.target.value)} minLength={2} maxLength={255} required autoFocus />
                </Field>
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="Review period start" htmlFor="period-start"><Input id="period-start" type="date" value={periodStart} onChange={(event) => setPeriodStart(event.target.value)} required /></Field>
                  <Field label="Review period end" htmlFor="period-end"><Input id="period-end" type="date" value={periodEnd} min={periodStart || undefined} onChange={(event) => setPeriodEnd(event.target.value)} required /></Field>
                </div>
                <Field label="Target due date (optional)" htmlFor="due-date"><Input id="due-date" type="date" value={dueDate} onChange={(event) => setDueDate(event.target.value)} /></Field>
                {error ? <p role="alert" className="status-note" data-tone="danger">{error}</p> : null}
                <div className="flex justify-end gap-3"><Button variant="ghost" onClick={() => router.back()}>Cancel</Button><Button type="submit" disabled={saving || !firmName.trim() || !periodStart || !periodEnd}>{saving ? "Creating…" : "Create workspace"}</Button></div>
              </form>
            </CardContent>
          </Card>
        )}
      </div>
    </AuthGate>
  );
}
