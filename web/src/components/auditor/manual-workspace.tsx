"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { AuthGate } from "@/components/auth/session";
import { PageHeader } from "@/components/shell/page";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadState } from "@/components/ui/load-state";
import { EmptyState } from "@/components/ui/empty-state";
import { FolderOpen } from "lucide-react";
import { AuditorActivityFeed } from "@/components/auditor/activity-feed";
import { AuditorUpcomingTasks } from "@/components/auditor/upcoming-tasks";
import {
  getClients,
  getWorkspace,
  requestFollowUp,
  saveDecision,
  sendFeedback,
  type Assessment,
  type ClientSummary,
  type Decision,
  type Workspace,
} from "@/lib/workflow-api";

function Dashboard() {
  const [clients, setClients] = useState<ClientSummary[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    getClients()
      .then(setClients)
      .catch((error: Error) => setError(error.message));
  }, []);
  return (
    <>
      <PageHeader
        title="Client audits"
        description="Your assigned engagements. All audit decisions are made by a human."
      />
      {!clients && (
        <LoadState
          error={error}
          label="Loading assigned clients…"
          retry={() => window.location.reload()}
        />
      )}
      {clients?.length === 0 && (
        <EmptyState
          icon={FolderOpen}
          title="No assigned audits yet"
          description="Assigned client engagements will appear here. Contact the administrator if you expected an assignment."
        />
      )}
      <div className="grid items-start gap-6 xl:grid-cols-12">
        <section
          aria-labelledby="assigned-audits-title"
          className="xl:col-span-4"
        >
          <h2
            id="assigned-audits-title"
            className="mb-3 text-sm font-semibold text-foreground"
          >
            Assigned engagements
          </h2>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-1">
            {clients?.map((client) => (
              <Card key={client.id}>
                <CardHeader>
                  <CardTitle>{client.firmName}</CardTitle>
                </CardHeader>
                <CardContent className="grid gap-3">
                  <p>
                    {client.readiness.reviewed}/{client.readiness.total} requests
                    reviewed
                  </p>
                  <p>
                    {client.readiness.ready
                      ? "Ready for report drafting"
                      : "Review incomplete"}
                  </p>
                  <Link
                    className="font-medium text-brand-hover underline underline-offset-4"
                    href={`/auditor/engagements/${client.id}`}
                  >
                    Open audit workspace
                  </Link>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
        <div className="xl:col-span-5">
          <AuditorActivityFeed />
        </div>
        <div className="xl:col-span-3">
          <AuditorUpcomingTasks />
        </div>
      </div>
    </>
  );
}

function EngagementWorkspace({ id }: { id: string }) {
  const [data, setData] = useState<Workspace | null>(null);
  const [drafts, setDrafts] = useState<Record<string, Decision>>({});
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [search, setSearch] = useState("");
  const load = useCallback(async () => {
    setData(await getWorkspace(id));
  }, [id]);
  useEffect(() => {
    getWorkspace(id)
      .then(setData)
      .catch((error: Error) => setError(error.message));
  }, [id]);
  async function act(action: () => Promise<void>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await action();
      await load();
      setNotice("Saved. History updated.");
    } catch (error) {
      setError(
        error instanceof Error ? error.message : "Could not save the change.",
      );
    } finally {
      setBusy(false);
    }
  }
  if (!data)
    return (
      <LoadState
        error={error}
        label="Loading audit workspace…"
        retry={() => window.location.reload()}
      />
    );
  const filtered = data.requests.filter((request) =>
    `${request.requestId} ${request.title}`
      .toLowerCase()
      .includes(search.toLowerCase()),
  );
  return (
    <>
      <PageHeader
        title={data.firmName}
        description="Internal auditor workspace. Notes and evidence assessments are never shown to clients."
        actions={
          <Link className="underline" href="/auditor">
            All client audits
          </Link>
        }
      />
      <Card className="mb-5">
        <CardHeader>
          <CardTitle>Report readiness</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2">
          <p role="status">
            {data.readiness.ready
              ? "Ready for report drafting"
              : "Review incomplete"}{" "}
            — {data.readiness.reviewed}/{data.readiness.total} reviewed
          </p>
          <p className="text-sm text-muted">
            {data.readiness.meaning} Quinton’s rubric remains to be completed
            separately.
          </p>
          <details>
            <summary className="cursor-pointer">
              Show {data.readiness.blockers.length} blockers
            </summary>
            <ul className="mt-2 grid gap-1 text-sm">
              {data.readiness.blockers.map((blocker) => (
                <li key={blocker}>{blocker}</li>
              ))}
            </ul>
          </details>
        </CardContent>
      </Card>
      {error && (
        <p role="alert" className="mb-4 text-red-300">
          {error}
        </p>
      )}
      {notice && (
        <p role="status" className="mb-4 text-green-300">
          {notice}
        </p>
      )}
      <label className="mb-5 grid gap-2">
        Search audit requests
        <input
          className="rounded-lg border border-border bg-surface p-3"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
      </label>
      {!filtered.length && <p>No matching requests.</p>}
      <div className="grid gap-4">
        {filtered.map((request) => {
          const draft = drafts[request.id] ?? {
            applicability: request.applicability ?? "applicable",
            assessment: request.assessment ?? "unable_to_determine",
            notes: request.notes,
          };
          function change(changes: Partial<Decision>) {
            setDrafts((current) => ({
              ...current,
              [request.id]: { ...draft, ...changes },
            }));
          }
          return (
            <details
              key={request.id}
              className="rounded-xl border border-border bg-surface p-4"
            >
              <summary className="cursor-pointer font-medium">
                {request.requestId} — {request.title}
                <span className="ml-2 text-xs text-muted">
                  {request.applicability ?? "Undecided"} ·{" "}
                  {request.assessment?.replaceAll("_", " ") ?? "Not assessed"}
                </span>
              </summary>
              <div className="mt-4 grid gap-4">
                {request.restricted ? (
                  <p className="text-sm text-amber-300">
                    Human-only handling. Do not upload or record restricted
                    document content here.
                  </p>
                ) : null}
                {request.representation && (
                  <p>
                    Client representation:{" "}
                    {request.representation.replaceAll("_", " ")} —{" "}
                    {request.naReviewState}
                  </p>
                )}
                <h2 className="font-semibold">
                  Documents ({request.documents.length})
                </h2>
                {!request.documents.length && (
                  <p className="text-sm text-muted">
                    No portal documents received.
                  </p>
                )}
                {request.documents.map((doc) => (
                  <div
                    className="grid gap-2 rounded-lg border border-border p-3"
                    key={doc.id}
                  >
                    <p className="break-all font-medium">{doc.name}</p>
                    <p className="break-all text-xs text-muted">
                      SHA-256: {doc.sha256} · Version {doc.version} ·{" "}
                      {new Date(doc.uploadedAt).toLocaleString()}
                    </p>
                    <label className="grid gap-2 text-sm">
                      Intake feedback for {doc.name}
                      <select
                        aria-label={`Intake feedback for ${doc.name}`}
                        className="rounded-lg border border-border bg-surface p-2"
                        disabled={busy}
                        value=""
                        onChange={(event) => {
                          if (event.target.value)
                            void act(() =>
                              sendFeedback(
                                id,
                                request.id,
                                doc.id,
                                event.target.value,
                              ),
                            );
                        }}
                      >
                        <option value="">
                          Choose neutral document feedback
                        </option>
                        <option value="unreadable">Unreadable — replace</option>
                        <option value="wrong_document">
                          Wrong document — replace
                        </option>
                        <option value="wrong_period">
                          Wrong review period — replace
                        </option>
                        <option value="missing_pages">
                          Missing pages — more needed
                        </option>
                        <option value="usable">
                          File usable — clear replacement request
                        </option>
                      </select>
                    </label>
                  </div>
                ))}
                <label className="grid gap-2">
                  Applicability
                  <select
                    aria-label={`Applicability ${request.requestId}`}
                    className="rounded-lg border border-border bg-surface p-2"
                    value={draft.applicability}
                    disabled={busy}
                    onChange={(event) => {
                      const applicability = event.target
                        .value as Decision["applicability"];
                      change({
                        applicability,
                        assessment:
                          applicability === "not_applicable"
                            ? null
                            : "unable_to_determine",
                      });
                    }}
                  >
                    <option value="applicable">Applicable</option>
                    <option value="not_applicable">Not applicable</option>
                  </select>
                </label>
                {draft.applicability === "applicable" && (
                  <label className="grid gap-2">
                    Evidence assessment
                    <select
                      aria-label={`Evidence assessment ${request.requestId}`}
                      className="rounded-lg border border-border bg-surface p-2"
                      value={draft.assessment ?? "unable_to_determine"}
                      disabled={busy}
                      onChange={(event) =>
                        change({ assessment: event.target.value as Assessment })
                      }
                    >
                      <option value="supported">Supported</option>
                      <option value="partial">Partial</option>
                      <option value="conflicting">Conflicting</option>
                      <option value="unable_to_determine">
                        Unable to determine
                      </option>
                    </select>
                  </label>
                )}
                <label className="grid gap-2">
                  Internal notes
                  <textarea
                    aria-label={`Internal notes ${request.requestId}`}
                    className="min-h-24 rounded-lg border border-border bg-background p-3"
                    value={draft.notes}
                    maxLength={5000}
                    disabled={busy}
                    onChange={(event) => change({ notes: event.target.value })}
                    placeholder="Internal reasoning only; never paste restricted content."
                  />
                </label>
                <div className="flex flex-wrap gap-3">
                  <Button
                    disabled={busy}
                    onClick={() =>
                      void act(() => saveDecision(id, request.id, draft))
                    }
                  >
                    Save decision {request.requestId}
                  </Button>
                  {!request.restricted && (
                    <Button
                      variant="outline"
                      disabled={busy}
                      onClick={() =>
                        void act(() => requestFollowUp(id, request.id))
                      }
                    >
                      Request follow-up {request.requestId}
                    </Button>
                  )}
                </div>
              </div>
            </details>
          );
        })}
      </div>
      <section className="mt-8">
        <h2 className="mb-4 text-lg font-semibold">Change history</h2>
        <p className="mb-4 text-sm text-muted">
          Actor, time, and before/after values. Internal only.
        </p>
        {!data.history.length && <p>No workflow changes recorded yet.</p>}
        <ol className="grid gap-3">
          {data.history.map((event) => (
            <li key={event.id} className="rounded-lg border border-border p-3">
              <p className="text-sm">
                {event.actor} · {new Date(event.at).toLocaleString()} ·{" "}
                {event.action}
              </p>
              <details>
                <summary className="cursor-pointer text-sm text-muted">
                  Change details
                </summary>
                <pre className="mt-2 whitespace-pre-wrap break-all text-xs">
                  {JSON.stringify(event.details, null, 2)}
                </pre>
              </details>
            </li>
          ))}
        </ol>
      </section>
    </>
  );
}

export function ManualWorkspace({ engagementId }: { engagementId?: string }) {
  return (
    <AuthGate role="auditor">
      {engagementId ? <EngagementWorkspace id={engagementId} /> : <Dashboard />}
    </AuthGate>
  );
}
