"use client";
import { useState } from "react";
import { Dialog } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useSession } from "./session";
import { finishOnboarding } from "@/lib/onboarding-api";
import type { SessionUser } from "@/lib/api";
const flows = {
  auditor: [
    {
      title: "Your audit workspace",
      text: "Create a client workspace with its review period, then invite the client when you are ready.",
    },
    {
      title: "Review evidence",
      text: "Work through the 34 requests. Record applicability, assess documents and keep internal notes together.",
    },
    {
      title: "Prepare and approve",
      text: "Record workpapers, samples and findings in each engagement, assemble the report from approved findings, then send it through second review and partner sign-off. Manage invoices from your sidebar.",
    },
  ],
  client: [
    {
      title: "Welcome to your client portal",
      text: "Your engagement keeps document requests and collection progress in one place.",
    },
    {
      title: "Send your documents",
      text: "Use Upload to send files, and complete the questionnaire to explain what applies. Follow restricted-item instructions and coordinate directly with your auditor.",
    },
    {
      title: "Keep track",
      text: "Check your checklist for document feedback and your progress for resolved requests. When your auditor asks for a management response it appears under Responses requested; signed reports and invoices are listed under Report and Invoices.",
    },
  ],
};
export function Onboarding() {
  const { session } = useSession();
  const user = session?.user;
  return user ? <Walkthrough key={`${user.id}:${user.role}`} user={user} /> : null;
}

function Walkthrough({ user }: { user: SessionUser }) {
  const { finishOnboarding: updateSession } = useSession();
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const flow = flows[user.role];
  const current = flow[step];
  async function finish(action: "completed" | "skipped") {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const saved = await finishOnboarding(user.role, action);
      if (saved.state === "pending")
        throw new Error("Could not save your preference. Please retry.");
      updateSession(user.id, saved.state);
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Could not save your preference. Please retry.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <Dialog
      open={user.onboarding_state === null}
      onOpenChange={(value) => {
        if (!value) void finish("skipped");
      }}
      title={current.title}
      description={
        user.role === "auditor"
          ? "A quick tour for your audit firm."
          : "A quick tour of your engagement."
      }
    >
      <div
        className="mb-5 flex gap-2"
        role="group"
        aria-label={`Step ${step + 1} of 3`}
      >
        {flow.map((_, index) => (
          <span
            key={index}
            className={`h-1 flex-1 rounded-full ${index <= step ? "bg-accent" : "bg-border"}`}
          />
        ))}
      </div>
      <p className="mb-4 text-sm leading-relaxed text-muted">{current.text}</p>
      <p className="mb-4 text-xs text-subtle">{step + 1} of 3</p>
      {error && (
        <p role="alert" className="mb-4 text-sm text-danger-foreground">
          {error}
        </p>
      )}
      <div className="flex flex-wrap justify-between gap-2">
        <Button
          variant="ghost"
          disabled={busy}
          onClick={() => void finish("skipped")}
        >
          Skip tour
        </Button>
        <div className="flex gap-2">
          {step > 0 && (
            <Button
              variant="outline"
              disabled={busy}
              onClick={() => setStep(step - 1)}
            >
              Back
            </Button>
          )}
          <Button
            disabled={busy}
            onClick={() =>
              step === 2 ? void finish("completed") : setStep(step + 1)
            }
          >
            {step === 2 ? "Get started" : "Next"}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
