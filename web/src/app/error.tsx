"use client";
import Link from "next/link";
import { LoadState } from "@/components/ui/load-state";

export default function ErrorPage({ retry }: { retry: () => void }) {
  return (
    <main id="main-content" className="mx-auto min-h-screen max-w-xl px-[var(--space-4)] py-[var(--space-8)]">
      <h1 className="type-display mb-[var(--space-5)]">Something went wrong</h1>
      <LoadState
        error="Please retry. If this continues, contact your auditor; do not send documents in a support message."
        retry={retry}
      />
      <Link className="mt-[var(--space-5)] inline-flex min-h-[var(--control-height)] items-center text-sm text-brand underline underline-offset-4" href="/">
        Return to overview
      </Link>
    </main>
  );
}
