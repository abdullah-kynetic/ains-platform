"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowDownUp, Building2 } from "lucide-react";
import { AuthGate } from "@/components/auth/session";
import { PageHeader } from "@/components/shell/page";
import { Button, buttonVariants } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/table";
import { LoadState } from "@/components/ui/load-state";
import { Progress } from "@/components/ui/progress";
import { USE_MOCKS } from "@/lib/api";
import { getClients, type ClientSummary } from "@/lib/workflow-api";
import { TodayView } from "./today-view";
import { EngagementDrawer } from "./engagement-drawer";
import { AuditorActivityFeed } from "./activity-feed";
import { AuditorUpcomingTasks } from "./upcoming-tasks";

export function EngagementTable({ clients }: { clients: ClientSummary[] }) {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [sort, setSort] = useState<"firmName" | "reviewed">("firmName");
  const [ascending, setAscending] = useState(true);
  const [page, setPage] = useState(0);
  const [size, setSize] = useState(5);
  const [selected, setSelected] = useState<ClientSummary | null>(null);
  const filtered = clients
    .filter(
      (c) =>
        c.firmName.toLowerCase().includes(query.toLowerCase()) &&
        (status === "all" ||
          (status === "ready" ? c.readiness.ready : !c.readiness.ready)),
    )
    .sort(
      (a, b) =>
        (sort === "firmName"
          ? a.firmName.localeCompare(b.firmName)
          : a.readiness.reviewed - b.readiness.reviewed) * (ascending ? 1 : -1),
    );
  const pages = Math.max(1, Math.ceil(filtered.length / size));
  const current = Math.min(page, pages - 1);
  function order(column: typeof sort) {
    setAscending(sort === column ? !ascending : true);
    setSort(column);
    setPage(0);
  }
  return (
    <section
      aria-labelledby="engagement-table-title"
      className="rounded-xl bg-card border border-border shadow-card"
    >
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border p-4">
        <div>
          <h2 id="engagement-table-title" className="text-base font-medium">
            Assigned engagements
          </h2>
          <p className="mt-1 text-xs text-muted">
            Review progress or open an engagement workspace.
          </p>
        </div>
        <Badge>{clients.length} engagements</Badge>
      </div>
      <div className="flex flex-wrap items-center gap-2 px-4 py-3">
        <Input
          aria-label="Search engagements"
          placeholder="Search firms…"
          className="max-w-72"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setPage(0);
          }}
        />
        <Select
          aria-label="Filter engagement status"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(0);
          }}
        >
          <option value="all">All review states</option>
          <option value="review">In review</option>
          <option value="ready">Ready for drafting</option>
        </Select>
        {(query || status !== "all") && (
          <Button
            variant="ghost"
            onClick={() => {
              setQuery("");
              setStatus("all");
              setPage(0);
            }}
          >
            Clear filters
          </Button>
        )}
      </div>
      <Table bare>
        <caption className="sr-only">Assigned engagement records</caption>
        <THead>
          <TR>
            <TH
              aria-sort={
                sort === "firmName"
                  ? ascending
                    ? "ascending"
                    : "descending"
                  : "none"
              }
            >
              <button
                onClick={() => order("firmName")}
                className="flex items-center gap-2"
              >
                Firm <ArrowDownUp className="size-3" />
              </button>
            </TH>
            <TH>Review state</TH>
            <TH
              aria-sort={
                sort === "reviewed"
                  ? ascending
                    ? "ascending"
                    : "descending"
                  : "none"
              }
            >
              <button
                onClick={() => order("reviewed")}
                className="flex items-center gap-2"
              >
                Requests reviewed <ArrowDownUp className="size-3" />
              </button>
            </TH>
            <TH>Actions</TH>
          </TR>
        </THead>
        <TBody>
          {filtered.slice(current * size, (current + 1) * size).map((c) => (
            <TR key={c.id}>
              <TD>
                <span className="flex items-center gap-2.5">
                  <span className="grid size-7 shrink-0 place-items-center rounded-md bg-elevated text-muted">
                    <Building2 aria-hidden="true" className="size-4" />
                  </span>
                  <span>
                    <span className="block font-medium">{c.firmName}</span>
                    <span className="block text-xs text-muted">
                      Independent AML test
                    </span>
                  </span>
                </span>
              </TD>
              <TD>
                <Badge variant={c.readiness.ready ? "success" : "default"} dot>
                  {c.readiness.ready ? "Ready for drafting" : "In review"}
                </Badge>
              </TD>
              <TD>
                <div className="min-w-28">
                  <span className="mb-2 block text-xs tabular-nums">
                    {c.readiness.reviewed} / {c.readiness.total}
                  </span>
                  <Progress
                    value={
                      c.readiness.total
                        ? (c.readiness.reviewed / c.readiness.total) * 100
                        : 0
                    }
                  />
                </div>
              </TD>
              <TD>
                <div className="flex flex-wrap items-center gap-3">
                  <Button variant="outline" onClick={() => setSelected(c)}>
                    View engagement details
                  </Button>
                  <Link
                    className="text-xs font-medium text-foreground underline-offset-4 hover:underline"
                    href={`/auditor/engagements/${c.id}`}
                  >
                    Open audit workspace
                  </Link>
                </div>
              </TD>
            </TR>
          ))}
        </TBody>
      </Table>
      {!filtered.length && (
        <p role="status" className="p-8 text-center text-sm text-muted">
          No engagements match these filters.
        </p>
      )}
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border px-5 py-3">
        <p role="status" className="text-xs text-muted">
          {filtered.length} results · Page {current + 1} of {pages}
        </p>
        <div className="flex items-center gap-2">
          <Select
            aria-label="Rows per page"
            value={size}
            onChange={(e) => {
              setSize(Number(e.target.value));
              setPage(0);
            }}
          >
            {[5, 10, 20].map((n) => (
              <option key={n} value={n}>
                {n} rows
              </option>
            ))}
          </Select>
          <Button
            variant="outline"
            disabled={!current}
            onClick={() => setPage(current - 1)}
          >
            Previous
          </Button>
          <Button
            variant="outline"
            disabled={current + 1 >= pages}
            onClick={() => setPage(current + 1)}
          >
            Next
          </Button>
        </div>
      </div>
      <EngagementDrawer client={selected} onClose={() => setSelected(null)} />
    </section>
  );
}

function Portfolio({ tableOnly }: { tableOnly: boolean }) {
  const [clients, setClients] = useState<ClientSummary[] | null>(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    getClients()
      .then((data) => {
        if (active) {
          setClients(data);
          setError("");
        }
      })
      .catch(() => {
        if (active) setError("Assigned engagements could not be loaded.");
      });
    return () => {
      active = false;
    };
  }, [retry]);
  if (!clients)
    return <LoadState error={error} retry={() => setRetry(retry + 1)} />;
  return (
    <>
      <PageHeader
        title={tableOnly ? "Engagements" : "Today"}
        description={
          tableOnly
            ? "Manage your assigned engagements and review progress."
            : "What needs your attention."
        }
        actions={
          <Link href="/auditor/workspaces/new" className={buttonVariants()}>
            Create client workspace
          </Link>
        }
      />
      {USE_MOCKS && (
        <p className="mb-5 text-xs text-subtle">
          Synthetic demonstration workspace
        </p>
      )}
      {!tableOnly && <TodayView clients={clients} />}
      <EngagementTable clients={clients} />
      {!tableOnly && (
        <div className="mt-4 grid items-start gap-4 xl:grid-cols-2">
          <AuditorActivityFeed />
          <AuditorUpcomingTasks engagements={clients} />
        </div>
      )}
    </>
  );
}
export function AuditorPortfolio({
  tableOnly = false,
}: {
  tableOnly?: boolean;
}) {
  return (
    <AuthGate role="auditor">
      <Portfolio tableOnly={tableOnly} />
    </AuthGate>
  );
}
