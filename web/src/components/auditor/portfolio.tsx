"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ArrowDownUp,
  Building2,
  ClipboardCheck,
  FileCheck2,
  ListChecks,
} from "lucide-react";
import { AuthGate } from "@/components/auth/session";
import { PageHeader, Stat } from "@/components/shell/page";
import { Button, buttonVariants } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/table";
import { LoadState } from "@/components/ui/load-state";
import { Progress } from "@/components/ui/progress";
import { USE_MOCKS } from "@/lib/api";
import { getClients, type ClientSummary } from "@/lib/workflow-api";
import { EngagementDrawer } from "./engagement-drawer";
import { AuditorActivityFeed } from "./activity-feed";
import { AuditorUpcomingTasks } from "./upcoming-tasks";

// Native, labelled SVG charts keep the portfolio usable without animation or pointer interaction.
function PortfolioCharts({ clients }: { clients: ClientSummary[] }) {
  const reviewed = clients.reduce((n, c) => n + c.readiness.reviewed, 0);
  const total = clients.reduce((n, c) => n + c.readiness.total, 0);
  const pct = total ? Math.round((reviewed / total) * 100) : 0;
  const groups = [
    {
      name: "In review",
      value: clients.filter((c) => !c.readiness.ready).length,
    },
    {
      name: "Ready for drafting",
      value: clients.filter((c) => c.readiness.ready).length,
    },
  ];
  return (
    <section
      aria-label="Overview charts"
      className="mb-7 grid gap-5 lg:grid-cols-[1.6fr_1fr]"
    >
      <div className="rounded-xl border border-border bg-surface p-6">
        <div className="flex justify-between">
          <div>
            <h2 className="font-semibold">Engagement distribution</h2>
            <p className="mt-1 text-xs text-muted">
              Current assigned portfolio · engagements by review state
            </p>
          </div>
          <Badge variant="brand">Live snapshot</Badge>
        </div>
        <svg
          role="img"
          aria-labelledby="distribution-title"
          viewBox="0 0 560 160"
          className="mt-5 w-full"
        >
          <title id="distribution-title">
            {groups.map((g) => `${g.name}: ${g.value}`).join(". ")}
          </title>
          {[0, 1, 2, 3, 4].map((n) => (
            <line
              key={n}
              x1={155 + n * 90}
              x2={155 + n * 90}
              y1="10"
              y2="125"
              stroke="var(--color-border)"
              strokeDasharray="3 5"
            />
          ))}
          {groups.map((g, i) => (
            <g key={g.name}>
              <text
                x="0"
                y={43 + i * 65}
                fill="var(--color-muted)"
                fontSize="13"
              >
                {g.name}
              </text>
              <rect
                x="155"
                y={22 + i * 65}
                width={(g.value / Math.max(clients.length, 1)) * 320}
                height="32"
                rx="5"
                fill={i ? "var(--color-brand-violet)" : "var(--color-brand)"}
              />
              <text
                x={165 + (g.value / Math.max(clients.length, 1)) * 320}
                y={43 + i * 65}
                fill="var(--color-foreground)"
                fontSize="13"
              >
                {g.value}
              </text>
            </g>
          ))}
          <text x="155" y="153" fill="var(--color-muted)" fontSize="11">
            0
          </text>
          <text x="475" y="153" fill="var(--color-muted)" fontSize="11">
            {clients.length} total
          </text>
        </svg>
      </div>
      <div className="rounded-xl border border-border bg-surface p-6">
        <h2 className="font-semibold">Request review coverage</h2>
        <p className="mt-1 text-xs text-muted">
          Recorded human reviews across assigned engagements
        </p>
        <div className="mt-4 flex items-center gap-6">
          <svg
            role="img"
            aria-label={`${pct}% reviewed: ${reviewed} of ${total} requests`}
            viewBox="0 0 120 120"
            className="size-36 shrink-0"
          >
            <circle
              cx="60"
              cy="60"
              r="46"
              fill="none"
              stroke="var(--color-elevated)"
              strokeWidth="12"
            />
            <circle
              cx="60"
              cy="60"
              r="46"
              fill="none"
              stroke="var(--color-brand)"
              strokeWidth="12"
              strokeDasharray={`${pct * 2.89} 289`}
              transform="rotate(-90 60 60)"
            />
            <text
              x="60"
              y="65"
              textAnchor="middle"
              fill="var(--color-foreground)"
              fontSize="23"
              fontWeight="600"
            >
              {pct}%
            </text>
          </svg>
          <div className="grid gap-4 text-sm">
            <p>
              <span className="block text-xl font-semibold">{reviewed}</span>
              <span className="text-muted">Reviewed</span>
            </p>
            <p>
              <span className="block text-xl font-semibold">
                {total - reviewed}
              </span>
              <span className="text-muted">Remaining</span>
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

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
      className="rounded-xl border border-border bg-surface"
    >
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border p-5">
        <div>
          <h2 id="engagement-table-title" className="font-semibold">
            Assigned engagements
          </h2>
          <p className="mt-1 text-xs text-muted">
            Open a record to review activity and continue your work.
          </p>
        </div>
        <Badge>{clients.length} engagements</Badge>
      </div>
      <div className="flex flex-wrap gap-3 p-5">
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
      <Table>
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
                <span className="font-medium">{c.firmName}</span>
                <span className="mt-1 block text-xs text-muted">
                  Independent AML test
                </span>
              </TD>
              <TD>
                <Badge variant={c.readiness.ready ? "brand" : "default"}>
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
                    className="text-xs text-brand hover:underline"
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
        title={tableOnly ? "Engagements" : "Overview"}
        description={
          tableOnly
            ? "Manage your assigned engagements and review progress."
            : "Your audit operations, at a glance. Every review moves the work forward."
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
      {!tableOnly && (
        <>
          <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Stat
              label="Assigned engagements"
              value={clients.length}
              hint="Your active review portfolio"
              icon={<Building2 className="size-4" />}
            />
            <Stat
              label="Requests reviewed"
              value={clients.reduce((n, c) => n + c.readiness.reviewed, 0)}
              hint="Human review recorded"
              icon={<ClipboardCheck className="size-4" />}
            />
            <Stat
              label="Requests remaining"
              value={clients.reduce(
                (n, c) => n + c.readiness.total - c.readiness.reviewed,
                0,
              )}
              hint="Across assigned engagements"
              icon={<ListChecks className="size-4" />}
            />
            <Stat
              label="Ready for drafting"
              value={clients.filter((c) => c.readiness.ready).length}
              hint="Auditor sign-off still required"
              icon={<FileCheck2 className="size-4" />}
            />
          </div>
          <PortfolioCharts clients={clients} />
        </>
      )}
      <EngagementTable clients={clients} />
      {!tableOnly && (
        <div className="mt-6 grid items-start gap-5 xl:grid-cols-2">
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
