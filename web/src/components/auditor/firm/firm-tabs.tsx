"use client";

import Image from "next/image";
import { useRef, useState } from "react";
import { Copy, ImagePlus, LayoutTemplate, Plus, Trash2, UserPlus } from "lucide-react";
import { PageHeader } from "@/components/shell/page";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { changeRole, deleteTemplate, getBranding, getRubric, inviteMember, listTeam, listTemplates, removeMember, saveBranding, saveRubricItem, saveTemplate, uploadBrandingLogo, type FirmBranding, type RequestTemplate, type RubricItem, type TeamRole } from "@/lib/api/index";
import { USE_MOCKS } from "@/lib/api";
import { sectionName } from "@/lib/mock/seed";
import { Loading, MockNotice, useAsync, useMutation } from "../kit";

const roles: { value: TeamRole; label: string; help: string }[] = [
  { value: "partner", label: "Partner", help: "Signs reports" },
  { value: "reviewer", label: "Second reviewer", help: "Approves before sign-off" },
  { value: "auditor", label: "Auditor", help: "Prepares workpapers and findings" },
  { value: "admin", label: "Admin", help: "Manages the firm, no sign-off" },
];

export function TeamTab() {
  const { data, error, reload, setData } = useAsync(listTeam, []);
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<TeamRole>("auditor");
  const { busy, problem, run } = useMutation();
  return (
    <>
      <PageHeader title="Team and roles" description="Who can prepare, review and sign. Only a partner can sign a report." actions={<Button disabled={!data || busy} onClick={() => setOpen(true)}><UserPlus aria-hidden />Invite member</Button>} />
      {USE_MOCKS && <MockNotice />}
      {problem && <p role="alert" className="status-note mb-4" data-tone="warning">{problem}</p>}
      {!data ? <Loading error={error} retry={reload} label="Loading team…" /> : (
        <Table>
          <THead><TR><TH>Member</TH><TH>Role</TH><TH>Status</TH><TH><span className="sr-only">Remove</span></TH></TR></THead>
          <TBody>
            {data.map((m) => (
              <TR key={m.id}>
                <TD><span className="font-medium">{m.name}</span><div className="text-xs text-muted">{m.email}</div></TD>
                <TD className="w-56"><Select aria-label={`Role for ${m.name}`} value={m.role} disabled={busy} onChange={(e) => void run(() => changeRole(m.id, e.target.value as TeamRole), setData)}>{roles.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}</Select></TD>
                <TD>{m.status === "active" ? <Badge variant="success">Active</Badge> : <Badge variant="warning">Invited</Badge>}</TD>
                <TD className="text-right"><Button variant="ghost" size="icon" aria-label={`Remove ${m.name}`} disabled={busy} onClick={() => void run(() => removeMember(m.id), setData)}><Trash2 aria-hidden /></Button></TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}
      <ul className="mt-4 grid gap-1 text-xs text-muted sm:grid-cols-2">{roles.map((r) => <li key={r.value}><span className="font-medium text-foreground">{r.label}:</span> {r.help}</li>)}</ul>
      <Dialog open={open} onOpenChange={setOpen} title="Invite a team member" description="They get an invitation by email and set up two-factor sign-in on first use.">
        <form className="grid gap-3" onSubmit={(e) => { e.preventDefault(); void run(() => inviteMember(email.trim(), role), (team) => { setData(team); setOpen(false); setEmail(""); }); }}>
          {problem && <p role="alert" className="status-note" data-tone="warning">{problem}</p>}
          <Field label="Work email"><Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
          <Field label="Role"><Select value={role} onChange={(e) => setRole(e.target.value as TeamRole)}>{roles.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}</Select></Field>
          <div className="flex justify-end gap-2"><Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" disabled={busy || !/.+@.+\..+/.test(email)}>{busy ? "Sending…" : "Send invitation"}</Button></div>
        </form>
      </Dialog>
    </>
  );
}

function BrandingForm({ initial, onSaved }: { initial: FirmBranding; onSaved: () => void }) {
  const [b, setB] = useState(initial);
  const [msg, setMsg] = useState("");
  const { busy, problem, run } = useMutation();
  const file = useRef<HTMLInputElement>(null);
  function pick(f?: File) {
    if (!f) return;
    void run(() => uploadBrandingLogo(f), ({ logoUrl }) => {
      setB((current) => ({ ...current, logoUrl }));
      setMsg("Logo ready. Save branding to apply it.");
    });
  }
  return (
    <form className="grid max-w-2xl gap-4" onSubmit={(e) => { e.preventDefault(); void run(() => saveBranding(b), () => { setMsg("Branding saved."); onSaved(); }); }}>
      {problem && <p role="alert" className="status-note" data-tone="warning">{problem}</p>}
      <Card><CardContent className="grid gap-4">
        <Field label="Firm name" hint="Shown in client emails and the client portal header."><Input value={b.name} onChange={(e) => setB({ ...b, name: e.target.value })} required /></Field>
        <Field label="Tagline"><Input value={b.tagline} onChange={(e) => setB({ ...b, tagline: e.target.value })} /></Field>
        <div className="grid gap-2">
          <span className="text-sm font-medium">Logo</span>
          <div className="flex items-center gap-4">
            <div className="grid size-16 place-items-center overflow-hidden rounded-lg border border-border bg-elevated">{b.logoUrl ? <Image unoptimized src={b.logoUrl} alt={`${b.name} logo`} width={64} height={64} className="size-full object-contain" /> : <ImagePlus aria-hidden className="size-6 text-muted" />}</div>
            <div className="flex gap-2"><input ref={file} type="file" accept="image/png,image/jpeg,image/svg+xml" className="sr-only" aria-label="Upload logo" onChange={(e) => pick(e.target.files?.[0])} /><Button variant="outline" disabled={busy} onClick={() => file.current?.click()}>Upload logo</Button>{b.logoUrl && <Button variant="ghost" disabled={busy} onClick={() => setB({ ...b, logoUrl: null })}>Remove</Button>}</div>
          </div>
          <p className="text-xs text-muted">PNG, JPG or SVG, under 512 KB.</p>
        </div>
      </CardContent></Card>
      <div className="flex items-center gap-3"><Button type="submit" disabled={busy}>{busy ? "Saving…" : "Save branding"}</Button>{msg && <span role="status" className="text-sm text-muted">{msg}</span>}</div>
    </form>
  );
}
export function BrandingTab() {
  const { data, error, reload } = useAsync(getBranding, []);
  return (
    <>
      <PageHeader title="Branding" description="Your firm name and logo on the client portal and report cover." />
      {USE_MOCKS && <MockNotice>Synthetic preview data. The logo is kept in this browser.</MockNotice>}
      {!data ? <Loading error={error} retry={reload} label="Loading branding…" /> : <BrandingForm initial={data} onSaved={reload} />}
    </>
  );
}

export function RubricTab() {
  const { data, error, reload, setData } = useAsync(getRubric, []);
  const sections = [...new Set((data ?? []).map((r) => r.section))];
  const { busy, problem, run } = useMutation();
  const save = (item: RubricItem) => run(() => saveRubricItem(item), setData);
  return (
    <>
      <PageHeader title="Checklist rubric" description="Per request: whether it is in scope and what a pass looks like. Criteria stay empty until the partner approves them." />
      {USE_MOCKS && <MockNotice />}
      {problem && <p role="alert" className="status-note mb-4" data-tone="warning">{problem}</p>}
      {!data ? <Loading error={error} retry={reload} label="Loading rubric…" /> : (
        <div className="grid gap-4">
          {sections.map((s) => (
            <Card key={s}>
              <CardHeader><CardTitle>{sectionName(s)}</CardTitle></CardHeader>
              <CardContent className="divide-y divide-border">
                {data.filter((r) => r.section === s).map((r) => (
                  <div key={r.requestId} className="grid gap-2 py-3 first:pt-0 last:pb-0 md:grid-cols-[minmax(0,16rem)_1fr] md:gap-4">
                    <label className="flex items-start gap-2 text-sm"><input type="checkbox" className="mt-0.5 size-4 accent-foreground" checked={r.enabled} disabled={busy} onChange={(e) => void save({ ...r, enabled: e.target.checked })} /><span><span className="font-mono text-xs text-muted">{r.requestId}</span><br /><span className="font-medium">{r.title}</span></span></label>
                    <Textarea aria-label={`Pass criteria for ${r.requestId}`} className="min-h-16" placeholder="Pass criteria (set by the partner)" defaultValue={r.criteria} disabled={busy} onBlur={(e) => { if (e.target.value !== r.criteria) void save({ ...r, criteria: e.target.value }); }} />
                  </div>
                ))}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}

const kinds: RequestTemplate["kind"][] = ["introducing", "retail", "clearing", "custom"];
const kindLabel: Record<RequestTemplate["kind"], string> = { introducing: "Introducing BD", retail: "Retail BD", clearing: "Self-clearing BD", custom: "Custom" };

function TemplateForm({ template, rubric, onClose, onSaved }: { template?: RequestTemplate; rubric: RubricItem[]; onClose: () => void; onSaved: () => void }) {
  const { busy, problem, run } = useMutation();
  const [name, setName] = useState(template?.name ?? "");
  const [kind, setKind] = useState<RequestTemplate["kind"]>(template?.kind ?? "custom");
  const [description, setDescription] = useState(template?.description ?? "");
  const [ids, setIds] = useState<string[]>(template?.requestIds ?? rubric.map((r) => r.requestId));
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()} className="max-w-2xl" title={template?.id ? "Edit template" : "New template"} description="Choose which of the 34 requests a new engagement starts with.">
      <form className="grid gap-3" onSubmit={(e) => { e.preventDefault(); void run(() => saveTemplate({ id: template?.id, name, kind, description, requestIds: ids }), () => { onSaved(); onClose(); }); }}>
        {problem && <p role="alert" className="status-note" data-tone="warning">{problem}</p>}
        <Field label="Name"><Input value={name} onChange={(e) => setName(e.target.value)} required /></Field>
        <Field label="Firm type"><Select value={kind} onChange={(e) => setKind(e.target.value as RequestTemplate["kind"])}>{kinds.map((k) => <option key={k} value={k}>{kindLabel[k]}</option>)}</Select></Field>
        <Field label="Description"><Textarea className="min-h-16" value={description} onChange={(e) => setDescription(e.target.value)} /></Field>
        <fieldset className="grid max-h-56 gap-1 overflow-y-auto rounded-lg border border-border p-3">
          <legend className="px-1 text-sm font-medium">Requests ({ids.length} of {rubric.length})</legend>
          {rubric.map((r) => <label key={r.requestId} className="flex items-center gap-2 text-sm"><input type="checkbox" className="size-4 accent-foreground" checked={ids.includes(r.requestId)} onChange={(e) => setIds(e.target.checked ? [...ids, r.requestId] : ids.filter((x) => x !== r.requestId))} /><span className="font-mono text-xs text-muted">{r.requestId}</span>{r.title}</label>)}
        </fieldset>
        <div className="flex justify-end gap-2"><Button variant="ghost" onClick={onClose}>Cancel</Button><Button type="submit" disabled={busy || !name.trim() || ids.length === 0}>Save template</Button></div>
      </form>
    </Dialog>
  );
}

export function TemplatesTab() {
  const { data, error, reload } = useAsync(async () => ({ templates: await listTemplates(), rubric: await getRubric() }), []);
  const [editing, setEditing] = useState<RequestTemplate | "new" | null>(null);
  const { busy, problem, run } = useMutation();
  return (
    <>
      <PageHeader title="Request-list templates" description="Starting request lists by firm type. Introducing and retail broker-dealers need different lists." actions={<Button disabled={!data || busy} onClick={() => setEditing("new")}><Plus aria-hidden />New template</Button>} />
      {USE_MOCKS && <MockNotice />}
      {problem && <p role="alert" className="status-note mb-4" data-tone="warning">{problem}</p>}
      {!data ? <Loading error={error} retry={reload} label="Loading templates…" /> : data.templates.length === 0 ? <EmptyState icon={LayoutTemplate} title="No templates" /> : (
        <div className="grid gap-4 md:grid-cols-2">
          {data.templates.map((t) => (
            <Card key={t.id}>
              <CardHeader className="flex-row items-start justify-between gap-2"><CardTitle>{t.name}</CardTitle><Badge variant="brand">{kindLabel[t.kind]}</Badge></CardHeader>
              <CardContent className="grid gap-3"><p className="text-sm text-muted">{t.description}</p><p className="text-sm tabular-nums">{t.requestIds.length} of {data.rubric.length} requests</p>
                <div className="flex flex-wrap gap-2"><Button size="sm" variant="outline" onClick={() => setEditing(t)}>Edit</Button><Button size="sm" variant="ghost" onClick={() => setEditing({ ...t, id: "", name: `${t.name} (copy)` })}><Copy aria-hidden />Duplicate</Button>{t.id !== "tpl-all" && <Button size="sm" variant="ghost" disabled={busy} onClick={() => void run(() => deleteTemplate(t.id), reload)}>Delete</Button>}</div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
      {editing && data && <TemplateForm key={editing === "new" ? "new" : editing.id || "copy"} template={editing === "new" ? undefined : editing} rubric={data.rubric} onClose={() => setEditing(null)} onSaved={reload} />}
    </>
  );
}
