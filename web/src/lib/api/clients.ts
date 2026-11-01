import { delay, readStore, updateStore, uid } from "../mock/store";
import { seedClients, seedEngagements } from "../mock/seed";
import type { ClientProfile, Contact, EngagementSummary } from "./types";

const clientsKey = "kien-mock-clients-v1";
const clients = () => readStore(clientsKey, seedClients);

// TODO(backend): GET /auditor/clients -> ClientProfile[]
export async function listClientProfiles(): Promise<ClientProfile[]> {
  return delay(clients());
}

// TODO(backend): GET /auditor/clients/{id} -> ClientProfile | 404
export async function getClientProfile(id: string): Promise<ClientProfile | null> {
  return delay(clients().find((c) => c.id === id) ?? null);
}

// TODO(backend): POST /auditor/clients/{id}/contacts -> Contact
export async function addContact(clientId: string, input: Omit<Contact, "id" | "primary">): Promise<Contact> {
  const contact: Contact = { ...input, id: uid("ct"), primary: false };
  updateStore(clientsKey, seedClients, (all) => {
    all.find((c) => c.id === clientId)?.contacts.push(contact);
  });
  return delay(contact);
}

// TODO(backend): GET /auditor/engagements -> EngagementSummary[] (all assigned engagements)
export async function listEngagementSummaries(): Promise<EngagementSummary[]> {
  return delay(seedEngagements());
}

// TODO(backend): GET /auditor/engagements/{id}/summary -> EngagementSummary | 404
export async function getEngagementSummary(id: string): Promise<EngagementSummary | null> {
  return delay(seedEngagements().find((e) => e.id === id) ?? null);
}
