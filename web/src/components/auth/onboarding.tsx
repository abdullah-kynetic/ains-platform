"use client";
import { useEffect, useState } from "react";
import { Dialog } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useSession } from "./session";
import { getOnboarding, finishOnboarding } from "@/lib/onboarding-api";
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
      text: "Draft the engagement report and review every finding. Finalize the version you approve; manage invoices from your sidebar.",
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
      text: "Check your checklist for document feedback and your progress for resolved requests. Your auditor handles findings and report approval separately.",
    },
  ],
};
export function Onboarding() {
  const { session } = useSession();
  const user = session?.user;
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    if (user)
      getOnboarding(user.role)
        .then((state) => {
          if (active) {
            setStep(0);
            setOpen(state.state === "pending");
          }
        })
        .catch(() => {
          /* A temporary preference failure never blocks sign-in; retry on the next visit. */
        });
    return () => {
      active = false;
    };
  }, [user?.id, user?.role, user]);
  if (!user) return null;
  const flow = flows[user.role];
  const current = flow[step];
  async function finish(action: "completed" | "skipped") {
    if (!user || busy) return;
    setBusy(true);
    setError("");
    try {
      await finishOnboarding(user.role, action);
      setOpen(false);
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
      open={open}
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
