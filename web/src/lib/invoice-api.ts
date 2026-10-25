import { apiRequest, USE_MOCKS } from "./api";

export type InvoiceStatus = "draft" | "sent" | "paid" | "void";
export type InvoiceLine = {
  description: string;
  quantity: string;
  rateCents: number;
  amountCents: number;
  position: number;
};
export type InvoiceEvent = {
  id: string;
  type: string;
  fromStatus: string | null;
  toStatus: string;
  amountCents: number | null;
  occurredAt: string;
  actorId: string;
  metadata: { paid_date?: string };
};
export type Invoice = {
  id: string;
  firmId: string;
  firmName: string;
  engagementId: string | null;
  number: number;
  status: InvoiceStatus;
  overdue: boolean;
  issueDate: string;
  dueDate: string;
  notes: string;
  currency: string;
  subtotalCents: number;
  totalCents: number;
  amountPaidCents: number;
  paidAt: string | null;
  createdAt: string;
  updatedAt: string;
  lineItems: InvoiceLine[];
  events: InvoiceEvent[];
};
export type InvoiceInput = Pick<
  Invoice,
  "firmId" | "engagementId" | "issueDate" | "dueDate" | "notes" | "currency"
> & {
  lineItems: Pick<InvoiceLine, "description" | "quantity" | "rateCents">[];
};
export type InvoiceOption = {
  id: string;
  firmId: string;
  firmName: string;
  label: string;
};
export type InvoiceFilters = {
  status?: string;
  client?: string;
  since?: string;
  until?: string;
  offset?: string;
};
const key = "ains-synthetic-invoices-v1";
export const today = () => new Date().toISOString().slice(0, 10);
export const money = (cents: number, currency: string) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency }).format(
    cents / 100,
  );
export const invoiceNumber = (number: number) =>
  `INV-${String(number).padStart(4, "0")}`;
// Integer hundredths avoid binary rounding drift for money and decimal quantities.
export function hundredths(value: string): number {
  if (!/^\d+(\.\d{1,2})?$/.test(value))
    throw new Error("Use a positive number with at most two decimals.");
  const [whole, fraction = ""] = value.split(".");
  const result = Number(whole) * 100 + Number(fraction.padEnd(2, "0"));
  if (!Number.isSafeInteger(result)) throw new Error("Amount is too large.");
  return result;
}
export const lineAmount = (quantity: string, cents: number) =>
  Math.floor((hundredths(quantity) * cents + 50) / 100);
const compute = (i: Invoice): Invoice => ({
  ...i,
  overdue:
    i.status === "sent" &&
    i.dueDate < today() &&
    i.amountPaidCents < i.totalCents,
});
const options: InvoiceOption[] = [
  {
    id: "eng-synthetic-001",
    firmId: "synthetic-firm",
    firmName: "Example Securities LLC (synthetic)",
    label: "2025-01-01 – 2025-12-31",
  },
];
function read(): Invoice[] {
  const saved = localStorage.getItem(key);
  if (saved) return (JSON.parse(saved) as Invoice[]).map(compute);
  return (["draft", "sent", "sent", "paid"] as InvoiceStatus[])
    .map((status, index) => ({
      id: `invoice-synthetic-${index + 1}`,
      firmId: options[0].firmId,
      firmName: options[0].firmName,
      engagementId: options[0].id,
      number: index + 1,
      status,
      overdue: status === "sent" && index === 2,
      issueDate: "2026-09-01",
      dueDate: index === 2 ? "2026-09-15" : "2099-12-31",
      notes: "Synthetic demo invoice. No payment or email is sent.",
      currency: "USD",
      subtotalCents: 250000,
      totalCents: 250000,
      amountPaidCents: status === "paid" ? 250000 : 0,
      paidAt: status === "paid" ? "2026-09-10" : null,
      createdAt: "2026-09-01T12:00:00Z",
      updatedAt: "2026-09-01T12:00:00Z",
      lineItems: [
        {
          description: "Independent AML testing (synthetic)",
          quantity: "1",
          rateCents: 250000,
          amountCents: 250000,
          position: 0,
        },
      ],
      events: [],
    }))
    .map(compute);
}
function write(invoices: Invoice[]) {
  localStorage.setItem(key, JSON.stringify(invoices));
}
export async function invoiceOptions(): Promise<InvoiceOption[]> {
  return USE_MOCKS ? options : apiRequest("/auditor/invoices/options");
}
export async function listInvoices(
  filters: InvoiceFilters = {},
): Promise<Invoice[]> {
  if (!USE_MOCKS)
    return apiRequest(
      `/auditor/invoices?${new URLSearchParams(Object.entries(filters).filter(([, v]) => Boolean(v)))}`,
    );
  return read()
    .filter(
      (i) =>
        (!filters.status ||
          (filters.status === "overdue"
            ? i.overdue
            : i.status === filters.status)) &&
        (!filters.client || i.firmId === filters.client) &&
        (!filters.since || i.issueDate >= filters.since) &&
        (!filters.until || i.issueDate <= filters.until),
    )
    .sort((a, b) => b.number - a.number)
    .slice(Number(filters.offset ?? 0), Number(filters.offset ?? 0) + 100);
}
export async function getInvoice(id: string): Promise<Invoice> {
  if (!USE_MOCKS)
    return apiRequest(`/auditor/invoices/${encodeURIComponent(id)}`);
  const invoice = read().find((i) => i.id === id);
  if (!invoice) throw new Error("Invoice not found");
  return invoice;
}
export async function saveInvoice(
  input: InvoiceInput,
  id?: string,
): Promise<Invoice> {
  if (!USE_MOCKS)
    return apiRequest(
      `/auditor/invoices${id ? `/${encodeURIComponent(id)}` : ""}`,
      { method: id ? "PATCH" : "POST", body: JSON.stringify(input) },
    );
  const invoices = read();
  const old = invoices.find((i) => i.id === id);
  if (id && (!old || old.status !== "draft"))
    throw new Error("Only drafts are editable");
  const lineItems = input.lineItems.map((line, position) => ({
    ...line,
    position,
    amountCents: lineAmount(line.quantity, line.rateCents),
  }));
  const total = lineItems.reduce((sum, line) => sum + line.amountCents, 0);
  if (!total || total > 100000000000 || input.dueDate < input.issueDate)
    throw new Error("Check invoice dates and amounts.");
  const invoice: Invoice = {
    ...input,
    id: old?.id ?? crypto.randomUUID(),
    firmName:
      options.find((o) => o.firmId === input.firmId)?.firmName ??
      "Synthetic client",
    number: old?.number ?? Math.max(0, ...invoices.map((i) => i.number)) + 1,
    status: "draft",
    overdue: false,
    lineItems,
    subtotalCents: total,
    totalCents: total,
    amountPaidCents: 0,
    paidAt: null,
    createdAt: old?.createdAt ?? new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    events: [
      ...(old?.events ?? []),
      {
        id: crypto.randomUUID(),
        type: old ? "updated" : "created",
        fromStatus: old ? "draft" : null,
        toStatus: "draft",
        amountCents: null,
        occurredAt: new Date().toISOString(),
        actorId: "synthetic-auditor",
        metadata: {},
      },
    ],
  };
  write([...invoices.filter((i) => i.id !== invoice.id), invoice]);
  return invoice;
}
export async function invoiceAction(
  id: string,
  action: "sent" | "paid" | "void",
  payment?: { paidDate: string; amountCents: number },
): Promise<Invoice> {
  if (!USE_MOCKS)
    return apiRequest(`/auditor/invoices/${encodeURIComponent(id)}/${action}`, {
      method: "POST",
      ...(payment ? { body: JSON.stringify(payment) } : {}),
    });
  const invoices = read();
  const i = invoices.find((i) => i.id === id);
  if (!i) throw new Error("Invoice not found");
  const before = i.status;
  if (action === "sent") {
    if (i.status !== "draft") throw new Error("Only drafts can be marked sent");
    i.status = "sent";
  }
  if (action === "void") {
    if (!["draft", "sent"].includes(i.status) || i.amountPaidCents)
      throw new Error("Only unpaid invoices can be voided");
    i.status = "void";
  }
  if (action === "paid") {
    if (
      i.status !== "sent" ||
      !payment ||
      payment.amountCents <= 0 ||
      payment.amountCents > i.totalCents - i.amountPaidCents ||
      payment.paidDate < i.issueDate ||
      payment.paidDate > today()
    )
      throw new Error("Check payment date and remaining balance");
    i.amountPaidCents += payment.amountCents;
    if (i.amountPaidCents === i.totalCents) {
      i.status = "paid";
      i.paidAt = payment.paidDate;
    }
  }
  i.updatedAt = new Date().toISOString();
  i.events.push({
    id: crypto.randomUUID(),
    type: payment ? "payment" : action,
    fromStatus: before,
    toStatus: i.status,
    amountCents: payment?.amountCents ?? null,
    occurredAt: i.updatedAt,
    actorId: "synthetic-auditor",
    metadata: payment ? { paid_date: payment.paidDate } : {},
  });
  write(invoices);
  return compute(i);
}
