import Link from "next/link";
import {
  Activity,
  ClipboardCheck,
  FileUp,
  MessageSquareText,
  RefreshCw,
  type LucideIcon,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type ActivityKind = "upload" | "review" | "feedback" | "questionnaire";

type AuditorActivity = {
  id: string;
  kind: ActivityKind;
  actor: string;
  action: string;
  subject: string;
  context: string;
  occurredAt: string;
  href: string;
};

const activityVisuals: Record<
  ActivityKind,
  { icon: LucideIcon; className: string }
> = {
  upload: { icon: FileUp, className: "bg-info/10 text-info-foreground" },
  review: {
    icon: ClipboardCheck,
    className: "bg-brand-tint text-brand",
  },
  feedback: {
    icon: MessageSquareText,
    className: "bg-warning/10 text-warning-foreground",
  },
  questionnaire: {
    icon: RefreshCw,
    className: "bg-success/10 text-success-foreground",
  },
};

const syntheticActivity: AuditorActivity[] = [
  {
    id: "activity-upload-001",
    kind: "upload",
    actor: "Example Securities LLC",
    action: "uploaded new evidence for",
    subject: "AML-BD-001",
    context: "Board-approved AML compliance program · Synthetic PDF",
    occurredAt: "12 minutes ago",
    href: "/auditor/engagements/eng-synthetic-001",
  },
  {
    id: "activity-review-001",
    kind: "review",
    actor: "Synthetic Auditor",
    action: "recorded a human assessment for",
    subject: "AML-BD-018",
    context: "Customer Identification Program documentation",
    occurredAt: "38 minutes ago",
    href: "/auditor/engagements/eng-synthetic-001",
  },
  {
    id: "activity-feedback-001",
    kind: "feedback",
    actor: "Synthetic Auditor",
    action: "requested a replacement document for",
    subject: "AML-BD-009",
    context: "Client received document-level feedback only",
    occurredAt: "1 hour ago",
    href: "/auditor/engagements/eng-synthetic-001",
  },
  {
    id: "activity-questionnaire-001",
    kind: "questionnaire",
    actor: "Example Securities LLC",
    action: "updated its representation for",
    subject: "AML-BD-026",
    context: "Response is waiting for human review",
    occurredAt: "Yesterday",
    href: "/auditor/engagements/eng-synthetic-001",
  },
];

export function AuditorActivityFeed() {
  return (
    <section aria-labelledby="auditor-activity-title">
      <div className="mb-3 flex items-center gap-2.5">
        <Activity className="size-4 text-subtle" aria-hidden="true" />
        <h2
          id="auditor-activity-title"
          className="flex-1 text-sm font-semibold text-foreground"
        >
          Latest activity
        </h2>
        <Badge variant="brand" dot>
          Internal only
        </Badge>
      </div>
      <Card>
        <CardContent className="pt-5">
          <ol className="grid gap-0">
            {syntheticActivity.map((item, index) => {
              const visual = activityVisuals[item.kind];
              const Icon = visual.icon;
              return (
                <li key={item.id} className="relative flex gap-3 pb-5 last:pb-0">
                  {index < syntheticActivity.length - 1 ? (
                    <span
                      aria-hidden="true"
                      className="absolute top-8 bottom-0 left-[15px] w-px bg-border"
                    />
                  ) : null}
                  <span
                    className={cn(
                      "relative z-10 grid size-8 shrink-0 place-items-center rounded-full ring-4 ring-surface",
                      visual.className,
                    )}
                  >
                    <Icon className="size-3.5" aria-hidden="true" />
                  </span>
                  <div className="min-w-0 pt-0.5">
                    <p className="text-[13px] leading-5 text-muted">
                      <span className="font-medium text-foreground">
                        {item.actor}
                      </span>{" "}
                      {item.action}{" "}
                      <Link
                        href={item.href}
                        className="font-medium text-brand-hover hover:underline"
                      >
                        {item.subject}
                      </Link>
                    </p>
                    <p className="mt-1 text-xs leading-5 text-subtle">
                      {item.context}
                    </p>
                    <p className="mt-1 text-[11px] text-subtle">
                      {item.occurredAt}
                    </p>
                  </div>
                </li>
              );
            })}
          </ol>
        </CardContent>
      </Card>
      <p className="mt-2 text-[11px] text-subtle">
        Synthetic preview activity. No client data is shown.
      </p>
    </section>
  );
}
