"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
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
import { getAuditorActivity, type ActivityKind, type AuditorActivity } from "@/lib/workflow-api";

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

function relativeTime(value: string) {
  const seconds = Math.round((new Date(value).getTime() - Date.now()) / 1000);
  const formatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
  if (Math.abs(seconds) < 60) return formatter.format(seconds, "second");
  const minutes = Math.round(seconds / 60);
  if (Math.abs(minutes) < 60) return formatter.format(minutes, "minute");
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) return formatter.format(hours, "hour");
  return formatter.format(Math.round(hours / 24), "day");
}

export function AuditorActivityFeed() {
  const [activity, setActivity] = useState<AuditorActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    getAuditorActivity()
      .then(setActivity)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Unable to load activity."))
      .finally(() => setLoading(false));
  }, []);
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
          {loading ? <p role="status" className="py-8 text-center text-xs text-subtle">Loading recent activity…</p> : null}
          {error ? <p role="alert" className="mb-3 rounded-lg border border-danger/20 bg-danger/5 px-3 py-2 text-xs text-danger">{error}</p> : null}
          <ol className="grid gap-0">
            {activity.map((item, index) => {
              const visual = activityVisuals[item.kind];
              const Icon = visual.icon;
              return (
                <li key={item.id} className="relative flex gap-3 pb-5 last:pb-0">
                  {index < activity.length - 1 ? (
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
                        href={`/auditor/engagements/${item.engagementId}`}
                        className="font-medium text-brand-hover hover:underline"
                      >
                        {item.subject}
                      </Link>
                    </p>
                    <p className="mt-1 text-xs leading-5 text-subtle">
                      {item.context}
                    </p>
                    <p className="mt-1 text-[11px] text-subtle">
                      {relativeTime(item.occurredAt)}
                    </p>
                  </div>
                </li>
              );
            })}
          </ol>
          {!loading && !activity.length ? <p className="py-8 text-center text-xs text-subtle">No recent activity for assigned engagements.</p> : null}
        </CardContent>
      </Card>
      <p className="mt-2 text-[11px] text-subtle">
        Internal activity for assigned engagements. Audit details remain in the protected workspace.
      </p>
    </section>
  );
}
