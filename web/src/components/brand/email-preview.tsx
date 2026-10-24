import Link from "next/link";
import {
  companyHost,
  companyName,
  companyUrl,
  invitationEmailSubject,
  productName,
} from "@/lib/brand";

export function InvitationEmailPreview({
  to,
  firmName,
  previewPath,
  expiresAt,
}: {
  to: string;
  firmName: string;
  previewPath: string;
  expiresAt: string;
}) {
  return (
    <article
      aria-label="Invitation email preview"
      className="overflow-hidden rounded-lg border border-border bg-surface"
    >
      <div className="border-b border-border bg-elevated px-4 py-3 text-sm">
        <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-subtle">
          Synthetic email preview
        </p>
        <p className="mt-2">
          <span className="text-subtle">From </span>
          <span className="font-medium text-foreground">{productName}</span>
          <span className="text-subtle"> · {companyName}</span>
        </p>
        <p>
          <span className="text-subtle">To </span>
          <span className="font-medium text-foreground">{to}</span>
        </p>
        <p className="mt-1 text-foreground">
          <span className="text-subtle">Subject </span>
          <span className="font-medium">{invitationEmailSubject}</span>
        </p>
      </div>
      <div className="grid gap-3 px-4 py-4 text-sm text-foreground">
        <p className="text-base font-semibold">
          {productName} by {companyName}
        </p>
        <p>You are invited to the {productName} workspace for {firmName}.</p>
        <p className="text-muted">
          This preview uses synthetic data only. No email was sent.
        </p>
        <Link
          className="font-medium text-brand underline underline-offset-4"
          href={previewPath}
        >
          Open invitation preview
        </Link>
        <p className="text-xs text-subtle">
          This link expires {new Date(expiresAt).toLocaleString()}.
        </p>
        <p className="border-t border-border pt-3 text-xs text-muted">
          {companyName} ·{" "}
          <a
            href={companyUrl}
            className="underline underline-offset-4"
            rel="noopener noreferrer"
          >
            {companyHost}
          </a>
        </p>
      </div>
    </article>
  );
}
