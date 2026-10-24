"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Search, ArrowUpRight } from "lucide-react";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import type { NavItem } from "./nav";

export function CommandPalette({ items }: { items: NavItem[] }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const input = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const results = items.filter((item) => item.label.toLowerCase().includes(query.toLowerCase()));
  useEffect(() => {
    function shortcut(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((value) => !value);
        setQuery("");
      }
    }
    window.addEventListener("keydown", shortcut);
    return () => window.removeEventListener("keydown", shortcut);
  }, []);
  useEffect(() => { if (open) input.current?.focus(); }, [open]);
  function navigate(href: string) { setOpen(false); router.push(href); }
  return <>
    <button type="button" onClick={() => { setQuery(""); setOpen(true); }} aria-label="Search workspace" className="flex min-h-11 items-center gap-2 rounded-lg border border-border bg-background px-3 text-xs text-muted">
      <Search className="size-4" aria-hidden="true" /><span>Search workspace</span><kbd className="ml-5 hidden rounded border border-border bg-surface px-1.5 py-1 text-[10px] sm:block">⌘ K</kbd>
    </button>
    <Dialog open={open} onOpenChange={setOpen} title="Go to workspace" description="Find a page. Use Tab to choose a result, then Enter to open it.">
      <Input ref={input} aria-label="Search pages" placeholder="Where would you like to go?" value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && results[0]) { event.preventDefault(); navigate(results[0].href); } }} />
      <p className="mt-4 text-xs text-subtle" role="status">{results.length} matching pages</p>
      <div className="mt-2 grid gap-1">{results.map((item) => <button key={item.href} onClick={() => navigate(item.href)} className="flex items-center justify-between rounded-lg px-3 py-3 text-left text-sm hover:bg-brand-tint hover:text-brand">{item.label}<ArrowUpRight className="size-4" aria-hidden="true" /></button>)}</div>
      {!results.length && <p className="py-5 text-sm text-muted">No pages match. Try another search.</p>}
    </Dialog>
  </>;
}
