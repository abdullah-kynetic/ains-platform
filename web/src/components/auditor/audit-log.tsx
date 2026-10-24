"use client";
import { useEffect, useState } from "react";
import { AuthGate } from "@/components/auth/session";
import { PageHeader } from "@/components/shell/page";
import { Button } from "@/components/ui/button";
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
    <div className="mb-5 flex flex-wrap items-end gap-4"><label className="grid gap-1 text-sm">Firm<select className="rounded-md border border-border bg-surface p-2" value={firm} onChange={e => { setFirm(e.target.value); setOffset(0); setStatus(""); }}>{firms.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}</select></label><label className="grid gap-1 text-sm">Action<input className="rounded-md border border-border bg-surface p-2" placeholder="All actions" value={action} onChange={e => { setAction(e.target.value); setOffset(0); }} /></label><Button disabled={!firm} onClick={verify}>Verify chain</Button></div>
    {status && <p role="status" className="mb-4 text-sm">{status}</p>}{error && <div role="alert" className="mb-4">{error} <Button onClick={() => setRetry(retry + 1)}>Retry</Button></div>}{loading ? <p role="status">Loading audit log…</p> : <div className="overflow-x-auto rounded-xl border border-border bg-surface"><table className="w-full text-left text-sm"><caption className="sr-only">Firm audit events</caption><thead className="border-b border-border text-muted"><tr>{["Sequence", "Actor", "Action", "Target", "Timestamp", "IP"].map(h => <th key={h} scope="col" className="p-4 font-medium">{h}</th>)}</tr></thead><tbody>{rows.map(r => <tr key={r.id} className="border-b border-border last:border-0"><td className="p-4">{r.sequence}</td><td className="p-4">{r.actor_id ?? "System"}</td><td className="p-4">{r.action}</td><td className="p-4">{r.entity_type} · {r.entity_id}</td><td className="p-4"><time dateTime={r.created_at}>{new Date(r.created_at).toLocaleString()}</time></td><td className="p-4">{r.ip_address ?? "Unavailable"}</td></tr>)}</tbody></table>{!rows.length && <p className="p-5 text-sm text-muted">No audit entries match these filters.</p>}</div>}
    <div className="mt-4 flex gap-3"><Button disabled={!offset} onClick={() => setOffset(offset - 20)}>Previous</Button><Button disabled={!more} onClick={() => setOffset(offset + 20)}>Next</Button></div></>;
}
export function AuditLogPage() { return <AuthGate role="auditor"><Log /></AuthGate>; }
