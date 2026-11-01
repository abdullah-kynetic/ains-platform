"use client";

import Link from "next/link";
import { Bell, CalendarClock, CircleDollarSign, FileSignature, FileUp, FileWarning } from "lucide-react";
import { AuthGate } from "@/components/auth/session";
import { PageHeader } from "@/components/shell/page";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { listNotifications, markAllRead, markRead, unreadCount, type Notification } from "@/lib/api/index";
import { cn } from "@/lib/utils";
import { Loading, MockNotice, fmtDateTime, useAsync } from "./kit";

const icons: Record<Notification["kind"], typeof Bell> = { deadline: CalendarClock, upload: FileUp, finding: FileWarning, signoff: FileSignature, invoice: CircleDollarSign };

export function NotificationsCenter() {
  const { data, error, reload, setData } = useAsync(listNotifications, []);
  return (
    <AuthGate role="auditor">
      <PageHeader title="Notifications" description="Deadlines, uploads, responses and sign-offs across your engagements."
        actions={<Button variant="outline" disabled={!data || unreadCount(data) === 0} onClick={async () => setData(await markAllRead())}>Mark all as read</Button>} />
      <MockNotice />
      {!data ? <Loading error={error} retry={reload} label="Loading notifications…" /> : data.length === 0 ? (
        <EmptyState icon={Bell} title="You’re all caught up" description="New uploads, responses and deadlines show up here." />
      ) : (
        <ul className="divide-y divide-border rounded-xl border border-border bg-surface">
          {data.map((n) => {
            const Icon = icons[n.kind];
            return (
              <li key={n.id} className="flex items-start gap-3 px-4 py-3">
                <span className={cn("mt-0.5 grid size-8 shrink-0 place-items-center rounded-md bg-elevated", n.kind === "deadline" ? "text-deadline-foreground" : "text-muted")}><Icon aria-hidden className="size-4" /></span>
                <div className="min-w-0 flex-1">
                  <Link href={n.href} onClick={() => void markRead(n.id)} className={cn("text-sm underline-offset-4 hover:underline", n.read ? "text-foreground" : "font-semibold")}>{n.title}{!n.read && <span className="sr-only"> (unread)</span>}</Link>
                  <p className="text-sm text-muted">{n.detail}</p>
                  <p className="mt-0.5 text-xs text-subtle">{fmtDateTime(n.at)}</p>
                </div>
                {!n.read && <span aria-hidden className="mt-2 size-2 shrink-0 rounded-full bg-foreground" />}
              </li>
            );
          })}
        </ul>
      )}
    </AuthGate>
  );
}
