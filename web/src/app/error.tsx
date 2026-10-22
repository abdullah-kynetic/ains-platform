"use client";
import Link from "next/link";
import { LoadState } from "@/components/ui/load-state";
export default function ErrorPage({ retry }: { retry: () => void }) {
  return (
    <main id="main-content" className="mx-auto max-w-xl p-6">
      <h1 className="mb-5 text-2xl font-semibold">Something went wrong</h1>
      <LoadState
        error="Please retry. If this continues, contact your auditor; do not send documents in a support message."
        retry={retry}
      />
      <Link className="mt-5 inline-block underline" href="/">
        Return to overview
      </Link>
    </main>
  );
}
