"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { cloneElement, useEffect, useId, useState } from "react";
import { Plus, Printer, ArrowLeft, Trash2, Receipt } from "lucide-react";
import { PageHeader } from "@/components/shell/page";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { USE_MOCKS } from "@/lib/api";
import {
  getInvoice,
  hundredths,
  invoiceAction,
  invoiceNumber,
  invoiceOptions,
  lineAmount,
  listInvoices,
  money,
  saveInvoice,
  today,
  type Invoice,
  type InvoiceFilters,
  type InvoiceOption,
} from "@/lib/invoice-api";

function DemoNote() {
  return USE_MOCKS ? (
    <p className="mt-4 text-xs text-subtle">
      Synthetic demo · Invoice metadata stays in this browser. No email or
      payment is sent.
    </p>
  ) : null;
}
function ErrorNote({ error }: { error: string }) {
  return error ? (
    <p role="alert" className="my-4 text-sm text-error">
      {error}
    </p>
  ) : null;
}
function Status({ invoice }: { invoice: Invoice }) {
  const label = invoice.overdue
    ? "Overdue"
    : invoice.status[0].toUpperCase() + invoice.status.slice(1);
  return (
    <Badge
      variant={
        invoice.overdue
          ? "warning"
          : invoice.status === "paid"
            ? "success"
            : invoice.status === "sent"
              ? "info"
              : "default"
      }
      dot
    >
      {label}
    </Badge>
  );
}
function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactElement<{ id?: string }>;
}) {
  const id = useId();
  return (
    <div className="flex min-w-0 flex-col gap-2 text-xs font-medium text-muted">
      <label htmlFor={id}>{label}</label>
      {cloneElement(children, { id })}
    </div>
  );
}
const detailPath = (id: string) =>
  `/auditor/invoices/${encodeURIComponent(id)}`;

export function InvoiceList() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [options, setOptions] = useState<InvoiceOption[]>([]);
  const [filters, setFilters] = useState<InvoiceFilters>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    Promise.all([listInvoices(filters), invoiceOptions()])
      .then(([data, choices]) => {
        if (active) {
          setInvoices(data);
          setOptions(choices);
          setError("");
        }
      })
      .catch((e) => {
        if (active)
          setError(
            e instanceof Error ? e.message : "Invoices could not be loaded",
          );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [filters, retry]);
  const clients = [...new Map(options.map((o) => [o.firmId, o])).values()];
  function filter(name: keyof InvoiceFilters, value: string) {
    setLoading(true);
    setFilters((f) => ({ ...f, [name]: value, offset: "0" }));
  }
  return (
    <>
      <PageHeader
        title="Invoices"
        description="Billing for your assigned client work."
        actions={
          <Link className={buttonVariants()} href="/auditor/invoices/new">
            <Plus aria-hidden className="size-4" />
            Create invoice
          </Link>
        }
      />
      <Card>
        <CardHeader>
          <CardTitle>Invoice register</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="mb-5 grid grid-cols-2 gap-3 xl:grid-cols-4">
            <Field label="Status">
              <Select
                value={filters.status ?? ""}
                onChange={(e) => filter("status", e.target.value)}
              >
                <option value="">All statuses</option>
                {["draft", "sent", "overdue", "paid", "void"].map((s) => (
                  <option key={s} value={s}>
                    {s[0].toUpperCase() + s.slice(1)}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Client">
              <Select
                value={filters.client ?? ""}
                onChange={(e) => filter("client", e.target.value)}
              >
                <option value="">All clients</option>
                {clients.map((o) => (
                  <option key={o.firmId} value={o.firmId}>
                    {o.firmName}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Issued from">
              <Input
                type="date"
                value={filters.since ?? ""}
                onChange={(e) => filter("since", e.target.value)}
              />
            </Field>
            <Field label="Issued through">
              <Input
                type="date"
                value={filters.until ?? ""}
                min={filters.since}
                onChange={(e) => filter("until", e.target.value)}
              />
            </Field>
          </div>
          <ErrorNote error={error} />
          {error && (
            <Button
              variant="outline"
              onClick={() => {
                setLoading(true);
                setRetry((r) => r + 1);
              }}
            >
              Retry
            </Button>
          )}
          {loading ? (
            <p role="status" className="py-8 text-sm text-muted">
              Loading invoices…
            </p>
          ) : (
            !error && (
              <>
                <ul className="divide-y divide-border" aria-label="Invoices">
                  {invoices.map((i) => (
                    <li key={i.id} className="py-4 first:pt-1">
                      <Link
                        href={detailPath(i.id)}
                        className="group flex flex-wrap items-start justify-between gap-3 rounded-lg p-2 transition-colors hover:bg-hover"
                      >
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-semibold group-hover:underline">
                            {invoiceNumber(i.number)}
                          </p>
                          <p className="mt-1 break-words text-sm text-muted">
                            {i.firmName}
                          </p>
                          <p className="mt-2 text-xs text-subtle">
                            Issued {i.issueDate} · Due {i.dueDate}
                          </p>
                        </div>
                        <div className="flex shrink-0 flex-col items-end gap-2">
                          <Status invoice={i} />
                          <p className="text-sm font-semibold tabular-nums">
                            {money(i.totalCents, i.currency)}
                          </p>
                          {i.amountPaidCents > 0 && i.status !== "paid" && (
                            <p className="text-xs text-muted">
                              {money(
                                i.totalCents - i.amountPaidCents,
                                i.currency,
                              )}{" "}
                              remaining
                            </p>
                          )}
                        </div>
                      </Link>
                    </li>
                  ))}
                </ul>
                {!invoices.length && (
                  <div className="py-10 text-center">
                    <Receipt
                      aria-hidden
                      className="mx-auto mb-3 size-6 text-subtle"
                    />
                    <p className="text-sm text-muted">
                      No invoices match these filters.
                    </p>
                  </div>
                )}
                <div className="mt-4 flex justify-end gap-2">
                  <Button
                    variant="outline"
                    disabled={!Number(filters.offset ?? 0)}
                    onClick={() => {
                      setLoading(true);
                      setFilters((f) => ({
                        ...f,
                        offset: String(
                          Math.max(0, Number(f.offset ?? 0) - 100),
                        ),
                      }));
                    }}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    disabled={invoices.length < 100}
                    onClick={() => {
                      setLoading(true);
                      setFilters((f) => ({
                        ...f,
                        offset: String(Number(f.offset ?? 0) + 100),
                      }));
                    }}
                  >
                    Next
                  </Button>
                </div>
              </>
            )
          )}
        </CardContent>
      </Card>
      <DemoNote />
    </>
  );
}

type LineDraft = {
  key: string;
  description: string;
  quantity: string;
  rate: string;
};
const newLine = (): LineDraft => ({
  key: crypto.randomUUID(),
  description: "",
  quantity: "1",
  rate: "",
});
function draftAmount(line: LineDraft) {
  try {
    return lineAmount(line.quantity, hundredths(line.rate));
  } catch {
    return 0;
  }
}

export function InvoiceForm({ id }: { id?: string }) {
  const router = useRouter();
  const [options, setOptions] = useState<InvoiceOption[]>([]);
  const [firmId, setFirmId] = useState("");
  const [engagementId, setEngagementId] = useState("");
  const [issueDate, setIssueDate] = useState(today());
  const [dueDate, setDueDate] = useState(today());
  const [currency, setCurrency] = useState("USD");
  const [notes, setNotes] = useState("");
  const [lines, setLines] = useState<LineDraft[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [editable, setEditable] = useState(true);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    Promise.all([invoiceOptions(), id ? getInvoice(id) : Promise.resolve(null)])
      .then(([choices, invoice]) => {
        if (!active) return;
        setOptions(choices);
        setError("");
        if (invoice) {
          setEditable(invoice.status === "draft");
          setFirmId(invoice.firmId);
          setEngagementId(invoice.engagementId ?? "");
          setIssueDate(invoice.issueDate);
          setDueDate(invoice.dueDate);
          setCurrency(invoice.currency);
          setNotes(invoice.notes);
          setLines(
            invoice.lineItems.map((l) => ({
              key: crypto.randomUUID(),
              description: l.description,
              quantity: l.quantity,
              rate: (l.rateCents / 100).toFixed(2),
            })),
          );
        } else {
          setFirmId(choices[0]?.firmId ?? "");
          setLines([newLine()]);
        }
      })
      .catch((e) => {
        if (active)
          setError(e instanceof Error ? e.message : "Form could not be loaded");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [id, retry]);
  const clients = [...new Map(options.map((o) => [o.firmId, o])).values()];
  function updateLine(key: string, change: Partial<LineDraft>) {
    setLines((ls) => ls.map((l) => (l.key === key ? { ...l, ...change } : l)));
  }
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const invoice = await saveInvoice(
        {
          firmId,
          engagementId: engagementId || null,
          issueDate,
          dueDate,
          currency,
          notes,
          lineItems: lines.map((l) => ({
            description: l.description.trim(),
            quantity: l.quantity,
            rateCents: hundredths(l.rate),
          })),
        },
        id,
      );
      router.push(detailPath(invoice.id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Invoice could not be saved");
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PageHeader
        title={id ? "Edit invoice" : "Create invoice"}
        description="Save a draft, then mark it sent when you have delivered it."
        actions={
          <Link
            className={buttonVariants({ variant: "outline" })}
            href={id ? detailPath(id) : "/auditor/invoices"}
          >
            <ArrowLeft aria-hidden className="size-4" />
            Back
          </Link>
        }
      />
      <ErrorNote error={error} />
      {loading ? (
        <p role="status">Loading invoice form…</p>
      ) : !options.length ? (
        <>
          <p className="text-sm text-muted">
            An assigned client engagement is required.
          </p>
          <Button
            variant="outline"
            onClick={() => {
              setLoading(true);
              setRetry((r) => r + 1);
            }}
          >
            Retry
          </Button>
        </>
      ) : !editable ? (
        <p role="alert">Only draft invoices can be edited.</p>
      ) : (
        <form onSubmit={submit}>
          <fieldset disabled={busy} className="space-y-5">
            <Card>
              <CardHeader>
                <CardTitle>Client & dates</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                <Field label="Client firm">
                  <Select
                    required
                    value={firmId}
                    onChange={(e) => {
                      setFirmId(e.target.value);
                      setEngagementId("");
                    }}
                  >
                    {clients.map((o) => (
                      <option key={o.firmId} value={o.firmId}>
                        {o.firmName}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label="Engagement (optional)">
                  <Select
                    value={engagementId}
                    onChange={(e) => setEngagementId(e.target.value)}
                  >
                    <option value="">No engagement</option>
                    {options
                      .filter((o) => o.firmId === firmId)
                      .map((o) => (
                        <option key={o.id} value={o.id}>
                          {o.label}
                        </option>
                      ))}
                  </Select>
                </Field>
                <Field label="Currency">
                  <Select
                    value={currency}
                    onChange={(e) => setCurrency(e.target.value)}
                  >
                    {["USD", "EUR", "GBP", "CAD", "AUD", "CHF"].map((c) => (
                      <option key={c}>{c}</option>
                    ))}
                  </Select>
                </Field>
                <Field label="Issue date">
                  <Input
                    required
                    type="date"
                    value={issueDate}
                    onChange={(e) => setIssueDate(e.target.value)}
                  />
                </Field>
                <Field label="Due date">
                  <Input
                    required
                    type="date"
                    min={issueDate}
                    value={dueDate}
                    onChange={(e) => setDueDate(e.target.value)}
                  />
                </Field>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between gap-3">
                  <CardTitle>Line items</CardTitle>
                  <Button
                    type="button"
                    variant="outline"
                    disabled={lines.length >= 100}
                    onClick={() => setLines((l) => [...l, newLine()])}
                  >
                    <Plus aria-hidden className="size-4" />
                    Add line
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="divide-y divide-border">
                  {lines.map((line, index) => (
                    <div
                      key={line.key}
                      className="grid grid-cols-2 items-end gap-3 py-4 sm:grid-cols-12"
                    >
                      <div className="col-span-2 sm:col-span-5">
                        <Field label={`Description ${index + 1}`}>
                          <Input
                            required
                            maxLength={1000}
                            value={line.description}
                            onChange={(e) =>
                              updateLine(line.key, {
                                description: e.target.value,
                              })
                            }
                          />
                        </Field>
                      </div>
                      <div className="sm:col-span-2">
                        <Field label={`Quantity ${index + 1}`}>
                          <Input
                            required
                            type="number"
                            min="0.01"
                            max="1000000"
                            step="0.01"
                            value={line.quantity}
                            onChange={(e) =>
                              updateLine(line.key, { quantity: e.target.value })
                            }
                          />
                        </Field>
                      </div>
                      <div className="sm:col-span-2">
                        <Field label={`Rate ${index + 1} (${currency})`}>
                          <Input
                            required
                            type="number"
                            min="0"
                            max="1000000"
                            step="0.01"
                            value={line.rate}
                            onChange={(e) =>
                              updateLine(line.key, { rate: e.target.value })
                            }
                          />
                        </Field>
                      </div>
                      <div className="flex min-w-0 items-center justify-between gap-2 sm:col-span-3">
                        <output
                          className="text-sm tabular-nums"
                          aria-label={`Amount ${index + 1}`}
                        >
                          {money(draftAmount(line), currency)}
                        </output>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          aria-label={`Remove line ${index + 1}`}
                          disabled={lines.length === 1}
                          onClick={() =>
                            setLines((ls) =>
                              ls.filter((l) => l.key !== line.key),
                            )
                          }
                        >
                          <Trash2 aria-hidden className="size-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mt-3 flex justify-end border-t border-border pt-4">
                  <p className="text-sm font-semibold">
                    Total{" "}
                    <output
                      aria-label="Invoice total"
                      aria-live="polite"
                      className="ml-6 text-xl tabular-nums"
                    >
                      {money(
                        lines.reduce((s, l) => s + draftAmount(l), 0),
                        currency,
                      )}
                    </output>
                  </p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Notes</CardTitle>
              </CardHeader>
              <CardContent>
                <Field label="Invoice notes">
                  <Textarea
                    rows={3}
                    maxLength={5000}
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                  />
                </Field>
              </CardContent>
            </Card>
            <div className="flex justify-end">
              <Button type="submit">{busy ? "Saving…" : "Save draft"}</Button>
            </div>
          </fieldset>
        </form>
      )}
      <DemoNote />
    </>
  );
}

export function InvoiceDetail({ id }: { id: string }) {
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [dialog, setDialog] = useState<"paid" | "void" | null>(null);
  const [paidDate, setPaidDate] = useState(today());
  const [amount, setAmount] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    getInvoice(id)
      .then((i) => {
        if (active) {
          setInvoice(i);
          setError("");
        }
      })
      .catch((e) => {
        if (active)
          setError(
            e instanceof Error ? e.message : "Invoice could not be loaded",
          );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [id, retry]);
  async function act(action: "sent" | "paid" | "void") {
    setBusy(true);
    setError("");
    try {
      setInvoice(
        await invoiceAction(
          id,
          action,
          action === "paid"
            ? { paidDate, amountCents: hundredths(amount) }
            : undefined,
        ),
      );
      setDialog(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Invoice action failed");
    } finally {
      setBusy(false);
    }
  }
  if (loading) return <p role="status">Loading invoice…</p>;
  if (!invoice)
    return (
      <>
        <ErrorNote error={error} />
        <Button
          variant="outline"
          onClick={() => {
            setLoading(true);
            setRetry((r) => r + 1);
          }}
        >
          Retry
        </Button>
      </>
    );
  const remaining = invoice.totalCents - invoice.amountPaidCents;
  return (
    <>
      <div className="invoice-controls">
        <PageHeader
          title={invoiceNumber(invoice.number)}
          badge={<Status invoice={invoice} />}
          description={invoice.firmName}
          actions={
            <>
              <Link
                className={buttonVariants({ variant: "outline" })}
                href="/auditor/invoices"
              >
                <ArrowLeft aria-hidden className="size-4" />
                Invoices
              </Link>
              <Button variant="outline" onClick={() => window.print()}>
                <Printer aria-hidden className="size-4" />
                Download PDF
              </Button>
              {invoice.status === "draft" && (
                <>
                  <Link
                    className={buttonVariants({ variant: "outline" })}
                    href={`${detailPath(id)}/edit`}
                  >
                    Edit draft
                  </Link>
                  <Button disabled={busy} onClick={() => void act("sent")}>
                    Mark sent
                  </Button>
                </>
              )}
              {invoice.status === "sent" && (
                <Button
                  disabled={busy}
                  onClick={() => {
                    setAmount((remaining / 100).toFixed(2));
                    setPaidDate(today());
                    setError("");
                    setDialog("paid");
                  }}
                >
                  Mark paid
                </Button>
              )}
              {["draft", "sent"].includes(invoice.status) &&
                !invoice.amountPaidCents && (
                  <Button
                    variant="ghost"
                    disabled={busy}
                    onClick={() => {
                      setError("");
                      setDialog("void");
                    }}
                  >
                    Void invoice
                  </Button>
                )}
            </>
          }
        />
      </div>
      {!dialog && <ErrorNote error={error} />}
      <Card className="invoice-print">
        <CardContent className="p-5 sm:p-8">
          <div className="flex flex-wrap justify-between gap-6 border-b border-border pb-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-subtle">
                Invoice
              </p>
              <h2 className="mt-2 text-2xl font-semibold">
                {invoiceNumber(invoice.number)}
              </h2>
              <p className="mt-3 text-sm text-muted">Bill to</p>
              <p className="mt-1 break-words text-sm font-medium">
                {invoice.firmName}
              </p>
            </div>
            <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
              <dt className="text-muted">Issued</dt>
              <dd>{invoice.issueDate}</dd>
              <dt className="text-muted">Due</dt>
              <dd>{invoice.dueDate}</dd>
              <dt className="text-muted">Currency</dt>
              <dd>{invoice.currency}</dd>
              <dt className="text-muted">Status</dt>
              <dd>{invoice.overdue ? "Overdue" : invoice.status}</dd>
            </dl>
          </div>
          <div className="overflow-x-auto">
            <table className="my-5 w-full text-left text-sm">
              <caption className="sr-only">Invoice line items</caption>
              <thead>
                <tr className="border-b border-border text-xs text-muted">
                  <th scope="col" className="py-3 pr-4 font-medium">
                    Description
                  </th>
                  <th scope="col" className="px-2 py-3 text-right font-medium">
                    Qty
                  </th>
                  <th scope="col" className="px-2 py-3 text-right font-medium">
                    Rate
                  </th>
                  <th scope="col" className="py-3 pl-2 text-right font-medium">
                    Amount
                  </th>
                </tr>
              </thead>
              <tbody>
                {invoice.lineItems.map((l, index) => (
                  <tr key={index} className="border-b border-border">
                    <td className="min-w-32 break-words py-4 pr-4">
                      {l.description}
                    </td>
                    <td className="px-2 py-4 text-right tabular-nums">
                      {l.quantity}
                    </td>
                    <td className="whitespace-nowrap px-2 py-4 text-right tabular-nums">
                      {money(l.rateCents, invoice.currency)}
                    </td>
                    <td className="whitespace-nowrap py-4 pl-2 text-right tabular-nums">
                      {money(l.amountCents, invoice.currency)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <dl className="ml-auto grid max-w-sm grid-cols-2 gap-3 text-sm">
            <dt className="text-muted">Subtotal</dt>
            <dd className="text-right tabular-nums">
              {money(invoice.subtotalCents, invoice.currency)}
            </dd>
            <dt className="font-semibold">Total</dt>
            <dd className="text-right font-semibold tabular-nums">
              {money(invoice.totalCents, invoice.currency)}
            </dd>
            <dt className="text-muted">
              Paid{invoice.paidAt ? ` · ${invoice.paidAt}` : ""}
            </dt>
            <dd className="text-right tabular-nums">
              {money(invoice.amountPaidCents, invoice.currency)}
            </dd>
            <dt className="border-t border-border pt-3 font-semibold">
              {invoice.status === "void" ? "Voided amount" : "Balance due"}
            </dt>
            <dd className="border-t border-border pt-3 text-right text-xl font-semibold tabular-nums">
              {money(remaining, invoice.currency)}
            </dd>
          </dl>
          {invoice.notes && (
            <div className="mt-8 border-t border-border pt-5">
              <h3 className="text-xs font-semibold text-muted">Notes</h3>
              <p className="mt-2 whitespace-pre-wrap break-words text-sm">
                {invoice.notes}
              </p>
            </div>
          )}
        </CardContent>
      </Card>
      <section className="invoice-controls mt-5">
        <Card>
          <CardHeader>
            <CardTitle>Invoice history</CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="divide-y divide-border">
              {invoice.events.map((e) => (
                <li
                  key={e.id}
                  className="flex flex-wrap justify-between gap-2 py-3 text-xs"
                >
                  <span className="font-medium capitalize">
                    {e.type}
                    {e.amountCents != null
                      ? ` · ${money(e.amountCents, invoice.currency)}`
                      : ""}
                    {e.metadata.paid_date
                      ? ` · Paid ${e.metadata.paid_date}`
                      : ""}
                  </span>
                  <span className="text-muted">
                    {e.occurredAt.slice(0, 10)} ·{" "}
                    {e.fromStatus ? `${e.fromStatus} → ` : ""}
                    {e.toStatus}
                  </span>
                </li>
              ))}
            </ol>
            {!invoice.events.length && (
              <p className="text-xs text-muted">
                No recorded events in this synthetic example.
              </p>
            )}
          </CardContent>
        </Card>
        <DemoNote />
      </section>
      <Dialog
        open={dialog !== null}
        onOpenChange={(open) => {
          if (!busy && !open) setDialog(null);
        }}
        dismissible={!busy}
        title={dialog === "paid" ? "Record payment" : "Void invoice"}
        description={
          dialog === "paid"
            ? "Record a payment already received. Partial payments keep the remaining balance open."
            : "This closes the unpaid invoice and retains its history."
        }
      >
        <ErrorNote error={error} />
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (dialog) void act(dialog);
          }}
        >
          <fieldset disabled={busy} className="space-y-4">
            {dialog === "paid" && (
              <>
                <Field label="Payment date">
                  <Input
                    required
                    type="date"
                    min={invoice.issueDate}
                    max={today()}
                    value={paidDate}
                    onChange={(e) => setPaidDate(e.target.value)}
                  />
                </Field>
                <Field label={`Amount received (${invoice.currency})`}>
                  <Input
                    required
                    type="number"
                    min="0.01"
                    max={(remaining / 100).toFixed(2)}
                    step="0.01"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                  />
                </Field>
              </>
            )}
            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setDialog(null)}
              >
                Cancel
              </Button>
              <Button type="submit">
                {busy
                  ? "Saving…"
                  : dialog === "paid"
                    ? "Record payment"
                    : "Confirm void"}
              </Button>
            </div>
          </fieldset>
        </form>
      </Dialog>
    </>
  );
}
