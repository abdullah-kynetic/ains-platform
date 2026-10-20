import { Badge } from "@/components/ui/badge";
import { STATUS_META, type ClientStatus } from "@/lib/checklist";

export function StatusBadge({ status }: { status: ClientStatus }) {
  const m = STATUS_META[status];
  return (
    <Badge variant={m.tone} dot title={m.help}>
      {m.label}
    </Badge>
  );
}
