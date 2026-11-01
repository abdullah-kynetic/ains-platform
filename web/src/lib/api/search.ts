import catalog from "../../../.generated/catalog.json";
import { delay, readStore } from "../mock/store";
import { seedClients, seedDocuments, seedEngagements, seedFindings } from "../mock/seed";
import type { SearchHit } from "./types";

// TODO(backend): GET /auditor/search?q= -> SearchHit[] (server-side, scoped to assigned engagements)
export async function searchAll(query: string): Promise<SearchHit[]> {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  const has = (...parts: string[]) => parts.join(" ").toLowerCase().includes(q);
  const hits: SearchHit[] = [
    ...seedClients().filter((c) => has(c.firmName, c.firmType, c.crd)).map((c) => ({ id: c.id, kind: "Client" as const, title: c.firmName, detail: c.firmType, href: `/auditor/clients/${c.id}` })),
    ...seedEngagements().filter((e) => has(e.firmName, e.period, e.stage)).map((e) => ({ id: e.id, kind: "Engagement" as const, title: e.firmName, detail: `${e.period} · ${e.stage}`, href: `/auditor/engagements/${e.id}` })),
    ...readStore("kien-mock-findings-v1", seedFindings).filter((f) => has(f.title, f.rule)).map((f) => ({ id: f.id, kind: "Finding" as const, title: f.title, detail: f.rule, href: `/auditor/engagements/${f.engagementId}/findings` })),
    ...catalog.requests.filter((r) => has(r.id, r.title)).map((r) => ({ id: r.id, kind: "Request" as const, title: `${r.id} · ${r.title}`, detail: "Checklist request", href: `/auditor/engagements/eng-synthetic-001/checklist` })),
    ...readStore("kien-mock-docs-v1", seedDocuments).filter((d) => has(d.name, d.requestId)).map((d) => ({ id: d.id, kind: "Document" as const, title: d.name, detail: d.requestId, href: `/auditor/engagements/${d.engagementId}/documents` })),
  ];
  return delay(hits.slice(0, 20), 40);
}
