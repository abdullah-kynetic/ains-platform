"use client";
import { useEffect, useState } from "react";
import { AuthGate } from "@/components/auth/session";
import { PageHeader } from "@/components/shell/page";
import { Button } from "@/components/ui/button";
import { LoadState } from "@/components/ui/load-state";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/table";
import { USE_MOCKS } from "@/lib/api";
import { auditEntries, auditFirms, verifyAudit, type AuditEntry } from "@/lib/audit-api";

export function AuditTimeline({ firm, entityId }: { firm: string; entityId: string }) {
  const [rows, setRows] = useState<AuditEntry[]>([]);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => { let active = true; auditEntries(firm, 0, "", entityId).then(r => { if (active) { setRows(r.items); setError(""); } }).catch(() => { if (active) setError("Audit entries could not be loaded."); }); return () => { active = false; }; }, [firm, entityId, retry]);
  return <section><h3 className="mb-3 font-semibold">Recent audit entries</h3>{error ? <div role="alert">{error} <button onClick={() => setRetry(retry + 1)}>Retry audit entries</button></div> : <ol className="ml-2 border-l border-border">{rows.map(r => <li key={r.id} className="relative pb-6 pl-6 text-sm"><span aria-hidden="true" className="absolute -left-1.5 top-1 size-3 rounded-full border-2 border-surface bg-brand" /><span className="font-medium">{r.action}</span><p className="mt-1 text-xs text-muted">{r.actor_id ?? "System"} · {r.entity_type}</p><time className="block text-xs text-muted" dateTime={r.created_at}>{new Date(r.created_at).toLocaleString()}</time></li>)}</ol>}</section>;
}
function Log() {
  const [firms, setFirms] = useState<Awaited<ReturnType<typeof auditFirms>>>([]);
  const [firm, setFirm] = useState(""); const [action, setAction] = useState(""); const [offset, setOffset] = useState(0);
  const [rows, setRows] = useState<AuditEntry[]>([]); const [more, setMore] = useState(false);
  const [error, setError] = useState(""); const [status, setStatus] = useState(""); const [loading, setLoading] = useState(true); const [retry, setRetry] = useState(0);
  useEffect(() => { let active = true; auditFirms().then(f => { if (active) { setFirms(f); setFirm(f[0]?.id ?? ""); setLoading(false); } }).catch(() => { if (active) { setError("Firms could not be loaded."); setLoading(false); } }); return () => { active = false; }; }, [retry]);
  useEffect(() => { if (!firm) return; let active = true; auditEntries(firm, offset, action).then(r => { if (active) { setRows(r.items); setMore(r.has_more); setError(""); } }).catch(() => { if (active) setError("Audit log could not be loaded."); }); return () => { active = false; }; }, [firm, action, offset, retry]);
  async function verify() { setStatus("Verifying…"); try { const r = await verifyAudit(firm); setStatus(`${USE_MOCKS ? "Synthetic demonstration: " : ""}${r.valid ? "Chain verified" : "Chain integrity failure"} · ${r.checked} entries checked`); } catch { setStatus("Verification failed. Please retry."); } }
  return <><PageHeader title="Audit Log" description="Append-only history of internal access and auditor actions." />{USE_MOCKS && <p className="mb-4 text-sm text-muted">Synthetic demo data · verification is simulated</p>}
    <div className="mb-4 flex flex-wrap items-end gap-2 p-1"><label className="grid min-w-0 flex-1 gap-[var(--space-2)] text-sm leading-snug sm:max-w-xs">Firm<Select value={firm} onChange={e => { setFirm(e.target.value); setOffset(0); setStatus(""); }}>{firms.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}</Select></label><label className="grid min-w-0 flex-1 gap-[var(--space-2)] text-sm leading-snug sm:max-w-xs">Action<Input placeholder="All actions" value={action} onChange={e => { setAction(e.target.value); setOffset(0); }} /></label><Button disabled={!firm} onClick={verify}>Verify chain</Button></div>
    {status && <p role="status" className="status-note mb-[var(--space-4)]" data-tone="info">{status}</p>}{error && <div role="alert" className="status-note mb-[var(--space-4)] flex flex-wrap items-center gap-[var(--space-3)]" data-tone="danger"><span>{error}</span> <Button onClick={() => setRetry(retry + 1)}>Retry</Button></div>}{loading ? <LoadState label="Loading audit log…" /> : <div className="bg-surface"><Table className="min-w-[720px] text-left"><caption className="sr-only">Firm audit events</caption><THead><TR>{["Sequence", "Actor", "Action", "Target", "Timestamp", "IP"].map(h => <TH key={h} scope="col">{h}</TH>)}</TR></THead><TBody>{rows.map(r => <TR key={r.id}><TD>{r.sequence}</TD><TD>{r.actor_id ?? "System"}</TD><TD>{r.action}</TD><TD>{r.entity_type} · {r.entity_id}</TD><TD><time dateTime={r.created_at}>{new Date(r.created_at).toLocaleString()}</time></TD><TD>{r.ip_address ?? "Unavailable"}</TD></TR>)}</TBody></Table>{!rows.length && <p className="px-[var(--space-5)] py-[var(--space-8)] text-center text-sm leading-normal text-muted">No audit entries match these filters.</p>}</div>}
    <div className="mt-4 flex gap-3"><Button disabled={!offset} onClick={() => setOffset(offset - 20)}>Previous</Button><Button disabled={!more} onClick={() => setOffset(offset + 20)}>Next</Button></div></>;
}
export function AuditLogPage() { return <AuthGate role="auditor"><Log /></AuthGate>; }
