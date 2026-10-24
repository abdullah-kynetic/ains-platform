import { apiRequest, USE_MOCKS } from "./api";
import { getClients, getWorkspace } from "./workflow-api";
export type AuditEntry = { id: string; actor_id: string | null; action: string; entity_type: string; entity_id: string | null; created_at: string; ip_address: string | null; sequence: number; row_hash: string; previous_hash: string };
export async function auditFirms() {
  return Array.from(new Map((await getClients()).map(c => [c.firmId ?? c.id, { id: c.firmId ?? c.id, name: c.firmName, engagementId: c.id }])).values());
}
export async function auditEntries(firm: string, offset = 0, action = "", entityId = ""): Promise<{ items: AuditEntry[]; has_more: boolean }> {
  if (!USE_MOCKS) return apiRequest(`/auditor/audit-log?${new URLSearchParams({ firm_id: firm, offset: String(offset), limit: "20", ...(action ? { action } : {}), ...(entityId ? { engagement_id: entityId } : {}) })}`);
  const history = (await getWorkspace(firm)).history;
  const items: AuditEntry[] = history.map((r, i) => ({ id: r.id, actor_id: r.actor, action: r.action, entity_type: "request", entity_id: r.entityId, created_at: r.at, ip_address: "192.0.2.10", sequence: i + 2, row_hash: "synthetic", previous_hash: "synthetic" })).reverse();
  items.push({ id: "synthetic-view", actor_id: "Synthetic Auditor", action: "engagement.view", entity_type: "engagement", entity_id: firm, created_at: "2026-10-24T15:00:00Z", ip_address: "192.0.2.10", sequence: 1, row_hash: "synthetic", previous_hash: "synthetic" });
  const filtered = items.filter(r => (!action || r.action === action) && (!entityId || firm === entityId || r.entity_id === entityId));
  return { items: filtered.slice(offset, offset + 20), has_more: filtered.length > offset + 20 };
}
export async function verifyAudit(firm: string): Promise<{ valid: boolean; checked: number }> {
  if (USE_MOCKS) return { valid: true, checked: (await auditEntries(firm)).items.length };
  return apiRequest(`/auditor/audit-log/verify-chain?firm_id=${encodeURIComponent(firm)}`);
}
