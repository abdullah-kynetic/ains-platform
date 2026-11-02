"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Mail, Phone, Plus, Users } from "lucide-react";
import { AuthGate } from "@/components/auth/session";
import { PageHeader } from "@/components/shell/page";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { addContact, getClientProfile, listClientProfiles } from "@/lib/api/index";
import { Loading, MockNotice, fmtDate, useAsync } from "./kit";

export function ClientsList() {
  const { data, error, reload } = useAsync(listClientProfiles, []);
  const [query, setQuery] = useState("");
  const [type, setType] = useState("all");
  const types = useMemo(() => [...new Set((data ?? []).map((c) => c.firmType))], [data]);
  const rows = (data ?? []).filter((c) => (type === "all" || c.firmType === type) && c.firmName.toLowerCase().includes(query.toLowerCase()));
  return (
    <AuthGate role="auditor">
      <PageHeader title="Clients" description="Every broker-dealer you test, with contacts and engagement history."
        actions={<Link href="/auditor/workspaces/new" className={buttonVariants()}><Plus aria-hidden />New client workspace</Link>} />
      <MockNotice />
      {!data ? <Loading error={error} retry={reload} label="Loading clients…" /> : (
        <>
          <div className="mb-4 flex flex-wrap gap-2">
            <Input aria-label="Search clients" placeholder="Search clients" className="w-full sm:w-64" value={query} onChange={(e) => setQuery(e.target.value)} />
            <div className="w-full sm:w-56"><Select aria-label="Filter by firm type" value={type} onChange={(e) => setType(e.target.value)}><option value="all">All firm types</option>{types.map((t) => <option key={t}>{t}</option>)}</Select></div>
          </div>
          {rows.length === 0 ? <EmptyState icon={Users} title="No clients match" description="Try a different search or firm type." /> : (
            <Table>
              <THead><TR><TH>Client</TH><TH>Firm type</TH><TH>Primary contact</TH><TH>Engagements</TH><TH>Latest</TH></TR></THead>
              <TBody>
                {rows.map((c) => (
                  <TR key={c.id}>
                    <TD><Link href={`/auditor/clients/${c.id}`} className="font-medium underline-offset-4 hover:underline">{c.firmName}</Link><div className="text-xs text-muted">{c.crd}</div></TD>
                    <TD>{c.firmType}</TD>
                    <TD>{c.contacts.find((x) => x.primary)?.name ?? "None"}</TD>
                    <TD>{c.engagements.length}</TD>
                    <TD>{c.engagements[0]?.status === "active" ? <Badge variant="brand">In progress</Badge> : <Badge variant="success">Complete</Badge>}</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          )}
        </>
      )}
    </AuthGate>
  );
}

function AddContact({ clientId, onAdded }: { clientId: string; onAdded: () => void }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", title: "", email: "", phone: "" });
  const [busy, setBusy] = useState(false);
  const valid = form.name.trim() && /.+@.+\..+/.test(form.email);
  return (
    <>
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}><Plus aria-hidden />Add contact</Button>
      <Dialog open={open} onOpenChange={setOpen} title="Add contact" description="Contacts receive invitations and report-ready notices for this client.">
        <form className="grid gap-3" onSubmit={async (e) => { e.preventDefault(); if (!valid) return; setBusy(true); await addContact(clientId, form); setBusy(false); setOpen(false); setForm({ name: "", title: "", email: "", phone: "" }); onAdded(); }}>
          <Field label="Name"><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></Field>
          <Field label="Title"><Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></Field>
          <Field label="Email"><Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required /></Field>
          <Field label="Phone"><Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></Field>
          <div className="flex justify-end gap-2"><Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" disabled={!valid || busy}>Save contact</Button></div>
        </form>
      </Dialog>
    </>
  );
}

export function ClientProfileView({ id }: { id: string }) {
  const { data, error, reload } = useAsync(() => getClientProfile(id), [id]);
  return (
    <AuthGate role="auditor">
      {data === null && !error ? <><PageHeader title="Client" /><Loading label="Loading client…" /></> : error ? <Loading error={error} retry={reload} /> : !data ? (
        <EmptyState icon={Users} title="Client not found" description="It may belong to another firm or no longer exist." action={<Link href="/auditor/clients" className={buttonVariants({ variant: "outline" })}>Back to clients</Link>} />
      ) : (
        <>
          <PageHeader title={data.firmName} badge={<Badge variant="brand">{data.firmType}</Badge>} description={`${data.crd} · ${data.state} · client since ${fmtDate(data.onboardedOn)}`} />
          <MockNotice />
          <div className="grid gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-1">
              <CardHeader><CardTitle>Firm details</CardTitle></CardHeader>
              <CardContent>
                <dl className="grid gap-3 text-sm">
                  {[["Firm type", data.firmType], ["Clearing arrangement", data.clearing], ["CRD (synthetic)", data.crd], ["Home state", data.state]].map(([k, v]) => (
                    <div key={k}><dt className="text-muted">{k}</dt><dd className="font-medium">{v}</dd></div>
                  ))}
                </dl>
              </CardContent>
            </Card>
            <Card className="lg:col-span-2">
              <CardHeader className="flex-row items-center justify-between"><CardTitle>Contacts</CardTitle><AddContact clientId={data.id} onAdded={reload} /></CardHeader>
              <CardContent>
                <ul className="divide-y divide-border">
                  {data.contacts.map((c) => (
                    <li key={c.id} className="flex flex-wrap items-center justify-between gap-2 py-3 first:pt-0 last:pb-0">
                      <div><p className="text-sm font-medium">{c.name} {c.primary && <Badge className="ml-1">Primary</Badge>}</p><p className="text-xs text-muted">{c.title}</p></div>
                      <div className="flex flex-wrap gap-4 text-sm text-muted"><span className="inline-flex items-center gap-1.5"><Mail aria-hidden className="size-3.5" />{c.email}</span><span className="inline-flex items-center gap-1.5"><Phone aria-hidden className="size-3.5" />{c.phone}</span></div>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </div>
          <h2 className="mt-6 mb-3 text-sm font-semibold">Engagement history</h2>
          <Table>
            <THead><TR><TH>Period</TH><TH>Status</TH><TH>Signed</TH><TH><span className="sr-only">Open</span></TH></TR></THead>
            <TBody>
              {data.engagements.map((e) => (
                <TR key={e.engagementId}>
                  <TD className="font-medium">{e.period}</TD>
                  <TD>{e.status === "active" ? <Badge variant="brand">In progress</Badge> : <Badge variant="success">Complete</Badge>}</TD>
                  <TD>{fmtDate(e.signedOn)}</TD>
                  <TD className="text-right">{e.engagementId.startsWith("eng-synthetic") ? <Link className="text-sm underline underline-offset-4" href={`/auditor/engagements/${e.engagementId}`}>Open workspace</Link> : <span className="text-xs text-muted">Archived</span>}</TD>
                </TR>
              ))}
            </TBody>
          </Table>
        </>
      )}
    </AuthGate>
  );
}
