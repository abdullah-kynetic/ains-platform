import { apiRequest, ApiError, USE_MOCKS } from "../api";
import { delay, readStore, updateStore, uid } from "../mock/store";
import { seedClients, seedEngagements } from "../mock/seed";
import type { ClientProfile, Contact, EngagementSummary } from "./types";

const clientsKey = "kien-mock-clients-v1";
const clients = () => readStore(clientsKey, seedClients);

// GET /auditor/clients -> ClientProfile[]
export async function listClientProfiles(): Promise<ClientProfile[]> {
  if (!USE_MOCKS) return apiRequest<ClientProfile[]>("/auditor/clients");
  return delay(clients());
}

// GET /auditor/clients/{id} -> ClientProfile | 404
export async function getClientProfile(id: string): Promise<ClientProfile | null> {
  if (!USE_MOCKS) return nullableRequest<ClientProfile>(`/auditor/clients/${encodeURIComponent(id)}`);
  return delay(clients().find((c) => c.id === id) ?? null);
}

// POST /auditor/clients/{id}/contacts -> Contact
export async function addContact(clientId: string, input: Omit<Contact, "id" | "primary">): Promise<Contact> {
  if (!USE_MOCKS) return apiRequest<Contact>(`/auditor/clients/${encodeURIComponent(clientId)}/contacts`, { method: "POST", body: JSON.stringify(input) });
  const contact: Contact = { ...input, id: uid("ct"), primary: false };
  updateStore(clientsKey, seedClients, (all) => {
    all.find((c) => c.id === clientId)?.contacts.push(contact);
  });
  return delay(contact);
}

// GET /auditor/engagements -> EngagementSummary[] (all assigned engagements)
export async function listEngagementSummaries(): Promise<EngagementSummary[]> {
  if (!USE_MOCKS) return apiRequest<EngagementSummary[]>("/auditor/engagements");
  return delay(seedEngagements());
}

// GET /auditor/engagements/{id}/summary -> EngagementSummary | 404
export async function getEngagementSummary(id: string): Promise<EngagementSummary | null> {
  if (!USE_MOCKS) return nullableRequest<EngagementSummary>(`/auditor/engagements/${encodeURIComponent(id)}/summary`);
  return delay(seedEngagements().find((e) => e.id === id) ?? null);
}

async function nullableRequest<T>(path: string): Promise<T | null> {
  try { return await apiRequest<T>(path); } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}
