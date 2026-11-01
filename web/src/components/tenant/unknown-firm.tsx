import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
} from "@/components/ui/card";
import type { TenantRejection } from "@/lib/tenant";

export function UnknownFirm({
  reason,
  host,
}: {
  reason: TenantRejection;
  host: string;
}) {
  const detail =
    reason === "apex"
      ? "Add the firm name in front of this domain. Firm portals open at an address like yourfirm.kiensolutions.com."
      : reason === "www"
        ? "www is the public site. Firm portals open at an address like yourfirm.kiensolutions.com."
        : reason === "unlisted"
          ? "This address is not a firm portal we recognize. Use the link from your invitation."
          : "Firm portals open at an address like yourfirm.kiensolutions.com. In local development, use yourfirm.localhost:3000.";

  return (
    <main
      id="main-content"
      data-tenant-state="unknown"
      data-tenant-reason={reason}
      className="min-h-screen px-4 py-16"
    >
      <div className="mx-auto grid w-full max-w-lg gap-6">
        <p className="text-center text-sm font-semibold tracking-[-0.02em]">
          Kien
        </p>
        <Card featured>
          <CardHeader>
            <h1 className="text-xl font-semibold">Unknown firm</h1>
            <CardDescription>
              We could not match this address to a firm. Use the portal link
              from your invitation.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 text-sm text-muted">
            <p>{detail}</p>
            {host ? (
              <p>
                This address was{" "}
                <span className="font-medium text-foreground">{host}</span>.
              </p>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
