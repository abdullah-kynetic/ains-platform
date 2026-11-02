import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";

export const metadata = { title: "Page not found" };

export default function NotFound() {
  return (
    <main id="main-content" className="mx-auto grid min-h-[60vh] max-w-md place-content-center gap-4 px-4 text-center">
      <p className="text-sm text-muted">Error 404</p>
      <h1 className="text-2xl font-semibold">We couldn’t find that page</h1>
      <p className="text-sm text-muted">The link may be old or the page may have moved. Your work is safe.</p>
      <div className="flex justify-center gap-2">
        <Link href="/" className={buttonVariants()}>Go to the start</Link>
        <Link href="/auditor" className={buttonVariants({ variant: "outline" })}>Auditor home</Link>
      </div>
    </main>
  );
}
