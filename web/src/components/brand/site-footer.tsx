import { companyHost, companyName, companyUrl, productName } from "@/lib/brand";
import { cn } from "@/lib/utils";

export function SiteFooter({ className }: { className?: string }) {
  return (
    <footer
      className={cn(
        "border-t border-border px-4 py-4 text-xs text-muted sm:px-8",
        className,
      )}
    >
      <div className="mx-auto flex w-full max-w-[1440px] flex-wrap items-center justify-between gap-x-4 gap-y-1">
        <p>
          {productName} by {companyName}
        </p>
        <a
          href={companyUrl}
          className="underline underline-offset-4 hover:text-foreground"
          rel="noopener noreferrer"
        >
          {companyHost}
        </a>
      </div>
    </footer>
  );
}
