"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { PageHeader } from "@/components/shell/page";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadState } from "@/components/ui/load-state";
import { Dialog } from "@/components/ui/dialog";
import { USE_MOCKS } from "@/lib/api";
import { getClients, type ClientSummary } from "@/lib/workflow-api";
import {
  createReport,
  getReport,
  listReports,
  saveReport,
  transitionReport,
  type Report,
  type ReportContent,
} from "@/lib/report-api";

export function ReportsList() {
  const router = useRouter();
  const [reports, setReports] = useState<Report[] | null>(null);
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    Promise.all([listReports(), getClients()])
      .then(([r, c]) => {
        setReports(r);
        setClients(c);
      })
      .catch((e: Error) => setError(e.message));
  }, []);
  async function open(id: string) {
    setBusy(true);
    setError("");
    try {
      const report = await createReport(id);
      router.push(`/auditor/reports/${report.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not open report");
      setBusy(false);
    }
  }
  return (
    <>
      <PageHeader
        title="Reports"
        description="Independent AML test reports for your assigned engagements."
      />
      {USE_MOCKS && (
        <p className="mb-4 text-xs text-muted">
          Synthetic demonstration · report metadata stays in this browser.
        </p>
      )}
      {error && <p role="alert">{error}</p>}
      {!reports && (
        <LoadState error={error} retry={() => window.location.reload()} />
      )}
      <div className="grid gap-4 md:grid-cols-2">
        {clients.map((client) => {
          const report = reports?.find((r) => r.engagementId === client.id);
          return (
            <Card key={client.id}>
              <CardHeader>
                <CardTitle>{client.firmName}</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-3">
                <p className="text-sm text-muted">
                  {report
                    ? `${report.status === "final" ? "Final" : "Draft"} · Version ${report.version}`
                    : "No report draft yet"}
                </p>
                <Button disabled={busy} onClick={() => void open(client.id)}>
                  {report ? "Open report" : "Draft report"}
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>
      {reports?.length === 0 && clients.length === 0 && (
        <p>No assigned engagements yet.</p>
      )}
    </>
  );
}

/** Native rich-text surface. Paste/drop accept text only; the API sanitizes all saved HTML. */
function RichText({
  label,
  html,
  onChange,
}: {
  label: string;
  html: string;
  onChange: (value: string) => void;
}) {
  const editor = useRef<HTMLDivElement>(null);
  function command(value: string) {
    editor.current?.focus();
    document.execCommand(value);
    if (editor.current) onChange(editor.current.innerHTML);
  }
  return (
    <div className="rounded-lg border border-border bg-surface">
      <div
        role="toolbar"
        aria-label={`${label} formatting`}
        className="flex flex-wrap gap-1 border-b border-border p-1"
      >
        {[
          ["bold", "Bold"],
          ["italic", "Italic"],
          ["insertUnorderedList", "Bullet list"],
        ].map(([cmd, title]) => (
          <button
            key={cmd}
            type="button"
            aria-label={`${title} in ${label}`}
            className="rounded px-3 text-sm hover:bg-hover"
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => command(cmd)}
          >
            {title}
          </button>
        ))}
      </div>
      <div
        ref={editor}
        role="textbox"
        aria-label={label}
        aria-multiline="true"
        contentEditable
        suppressContentEditableWarning
        className="report-rich min-h-32 p-4 text-sm"
        dangerouslySetInnerHTML={{ __html: html }}
        onInput={(e) => onChange(e.currentTarget.innerHTML)}
        onDrop={(e) => e.preventDefault()}
        onPaste={(e) => {
          e.preventDefault();
          document.execCommand(
            "insertText",
            false,
            e.clipboardData.getData("text/plain"),
          );
          if (editor.current) onChange(editor.current.innerHTML);
        }}
      />
    </div>
  );
}

export function ReportEditor({
  id,
  printView = false,
}: {
  id: string;
  printView?: boolean;
}) {
  const [report, setReport] = useState<Report | null>(null);
  const [content, setContent] = useState<ReportContent | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [attest, setAttest] = useState(false);
  useEffect(() => {
    getReport(id)
      .then((r) => {
        setReport(r);
        setContent(r.content);
      })
      .catch((e: Error) => setError(e.message));
  }, [id]);
  async function act(action: () => Promise<Report>, message: string) {
    setBusy(true);
    setError("");
    try {
      const result = await action();
      setReport(result);
      setContent(result.content);
      setDirty(false);
      setNotice(message);
      setConfirm(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save report");
    } finally {
      setBusy(false);
    }
  }
  if (!report || !content)
    return <LoadState error={error} retry={() => window.location.reload()} />;
  const editable = report.status === "draft" && !printView;
  function sectionChange(index: number, html: string) {
    setDirty(true);
    setContent(
      (current) =>
        current && {
          ...current,
          sections: current.sections.map((section, i) =>
            i === index ? { ...section, html } : section,
          ),
        },
    );
  }
  return (
    <>
      <div className="report-controls">
        <PageHeader
          title="Independent AML test report"
          description={`${report.snapshot.firmName} · ${report.status === "final" ? "Final · editing locked" : "Draft"}`}
          actions={
            <>
              <Link
                href="/auditor/reports"
                className={buttonVariants({ variant: "outline" })}
              >
                All reports
              </Link>
              {editable && (
                <Button
                  disabled={busy || !dirty}
                  onClick={() =>
                    void act(() => saveReport(report, content), "Draft saved.")
                  }
                >
                  Save draft
                </Button>
              )}
              {!printView && (
                <Link
                  aria-disabled={dirty}
                  href={dirty ? "#" : `/auditor/reports/${id}/print`}
                  className={buttonVariants({ variant: "outline" })}
                >
                  Print view
                </Link>
              )}
              {printView && (
                <Button onClick={() => window.print()}>Print / Save PDF</Button>
              )}
              {editable && (
                <Button
                  variant="outline"
                  disabled={busy || dirty}
                  onClick={() => {
                    setAttest(false);
                    setConfirm(true);
                  }}
                >
                  Finalize report
                </Button>
              )}
              {report.status === "final" && !printView && (
                <Button
                  disabled={busy}
                  onClick={() =>
                    void act(
                      () => transitionReport(report, "reopen"),
                      "Report reopened. History updated.",
                    )
                  }
                >
                  Reopen report
                </Button>
              )}
            </>
          }
        />
      </div>
      {USE_MOCKS && (
        <p className="report-controls mb-4 text-xs text-muted">
          Synthetic demonstration · no client delivery or signature.
        </p>
      )}
      {error && (
        <p role="alert" className="report-controls mb-4 text-danger-foreground">
          {error}
        </p>
      )}
      {notice && (
        <p role="status" className="report-controls mb-4">
          {notice}
        </p>
      )}
      {dirty && (
        <p role="status" className="report-controls mb-4 text-sm text-muted">
          Unsaved changes. Save before finalizing or printing.
        </p>
      )}
      <article
        className="report-print grid gap-4 rounded-xl bg-card p-4 ring-1 ring-foreground/10"
        aria-label="Independent AML test report"
      >
        <div className="grid gap-2 border-b border-border pb-5">
          <p className="text-xs font-semibold uppercase tracking-widest">
            Kien Solutions · Independent AML testing
          </p>
          <h2 className="text-2xl font-semibold">{report.snapshot.firmName}</h2>
          <p className="text-sm">Review period: {report.snapshot.period}</p>
          <p className="text-sm">Scope: {report.snapshot.scope}</p>
          <p className="text-sm font-medium">
            {report.status === "draft"
              ? "Draft · requires human review"
              : "Final · editing locked"}
          </p>
          <p className="text-xs text-muted">
            Confidential · Internal auditor report. Finalization records human
            approval; it is not a cryptographic signature or client delivery.
          </p>
        </div>
        {content.sections.map((section, index) => (
          <section
            key={`${report.id}-${report.version}-${index}`}
            className="grid gap-3"
          >
            <h3 className="text-lg font-semibold">{section.title}</h3>
            {editable ? (
              <RichText
                label={section.title}
                html={report.content.sections[index].html}
                onChange={(html) => sectionChange(index, html)}
              />
            ) : (
              <div
                className="report-rich text-sm"
                dangerouslySetInnerHTML={{ __html: section.html }}
              />
            )}
          </section>
        ))}
        <section className="grid gap-4">
          <h3 className="text-lg font-semibold">
            Checklist and per-item findings
          </h3>
          <p className="text-xs text-muted">
            Request statuses describe evidence collection. Record only
            human-reviewed findings. Restricted items show handling metadata
            only.
          </p>
          {report.snapshot.requests.map((item) => (
            <div
              key={item.requestId}
              className="report-request grid gap-2 border-t border-border pt-4"
            >
              <div className="flex flex-wrap justify-between gap-2 text-sm">
                <h4 className="font-medium">
                  {item.requestId} · {item.title}
                </h4>
                <span>
                  {item.status === "not_applicable"
                    ? "Does not apply"
                    : item.status.replaceAll("_", " ")}
                </span>
              </div>
              {item.restricted ? (
                <p className="text-xs text-muted">
                  Restricted · human handling only. No content retained here.
                </p>
              ) : editable ? (
                <label className="grid gap-2 text-xs text-muted">
                  Finding {item.requestId}
                  <textarea
                    aria-label={`Finding ${item.requestId}`}
                    className="min-h-20 rounded-lg border border-border bg-background p-3 text-sm text-foreground"
                    value={content.item_findings[item.requestId] ?? ""}
                    maxLength={5000}
                    onChange={(e) => {
                      setDirty(true);
                      setContent({
                        ...content,
                        item_findings: {
                          ...content.item_findings,
                          [item.requestId]: e.target.value,
                        },
                      });
                    }}
                  />
                </label>
              ) : (
                <p className="whitespace-pre-wrap text-sm">
                  {content.item_findings[item.requestId] ||
                    "No finding recorded."}
                </p>
              )}
            </div>
          ))}
        </section>
        {report.finalizedAt && (
          <p className="text-xs text-muted">
            Finalized {new Date(report.finalizedAt).toLocaleString()}
            {report.contentSha256 && (
              <>
                {" "}
                · SHA-256{" "}
                <span className="break-all font-mono">
                  {report.contentSha256}
                </span>
              </>
            )}
          </p>
        )}
      </article>
      <Dialog
        open={confirm}
        onOpenChange={setConfirm}
        title="Finalize report"
        description="Finalizing locks this version. You can reopen it later; both actions are recorded in the audit log."
      >
        <label className="mb-4 flex items-start gap-3 text-sm">
          <input
            type="checkbox"
            checked={attest}
            onChange={(e) => setAttest(e.target.checked)}
          />
          I reviewed this report and approve this version as final.
        </label>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => setConfirm(false)}>
            Cancel
          </Button>
          <Button
            disabled={!attest || busy}
            onClick={() =>
              void act(
                () => transitionReport(report, "finalize"),
                "Report finalized. Editing locked.",
              )
            }
          >
            Confirm finalization
          </Button>
        </div>
      </Dialog>
    </>
  );
}
