"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Hexagon } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/fleet", label: "Fleet" },
  { href: "/", label: "Audit" },
  { href: "/history", label: "Ledger" },
];

const STATUS_CHIPS = ["ATA 2026", "google-adk", "gemini-3.5-flash"];

export function BrandMark({ size = "md" }: { size?: "sm" | "md" }) {
  const box = size === "sm" ? "size-8" : "size-8";
  return (
    <span
      className={cn(
        "vf-glow flex items-center justify-center rounded-sm border border-emerald-400/35 bg-emerald-400/10",
        box
      )}
    >
      <Hexagon className="size-4 text-emerald-300" strokeWidth={2.2} />
    </span>
  );
}

export function AppShell({
  children,
  right,
}: {
  children: React.ReactNode;
  right?: React.ReactNode;
}) {
  const path = usePathname();

  return (
    <div className="vf-app relative min-h-screen bg-[#0b1220] text-slate-200">
      <header className="sticky top-0 z-30 w-full border-b border-[#1e2b45] bg-[#0b1220]/85 backdrop-blur-md">
        <div className="mx-auto flex w-full max-w-[1280px] flex-col gap-3 px-4 py-3 md:flex-row md:items-center md:justify-between md:gap-6 md:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <Link href="/fleet" className="flex min-w-0 items-center gap-3">
              <BrandMark />
              <span className="flex flex-col leading-none">
                <span className="text-[15px] font-semibold tracking-tight text-slate-50">
                  VeriFleet
                </span>
                <span className="mt-1 font-mono text-[9px] uppercase tracking-[0.2em] text-slate-500">
                  Fortified Enterprise Fleet
                </span>
              </span>
            </Link>
          </div>

          <nav aria-label="Console sections" className="flex min-w-0 items-center gap-4 overflow-x-auto md:ml-2 md:gap-6">
            {NAV.map((item) => {
              const active = item.href === "/" ? path === "/" : path.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "shrink-0 border-b-2 pb-1 font-mono text-[11px] uppercase tracking-[0.18em] transition",
                    active
                      ? "border-emerald-400 text-emerald-300"
                      : "border-transparent text-slate-500 hover:text-slate-200"
                  )}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="flex flex-wrap items-center gap-1.5">
            <ul className="flex flex-wrap items-center gap-1.5">
              {STATUS_CHIPS.map((chip) => (
                <li
                  key={chip}
                  className="vf-panel-inset flex items-center gap-1.5 rounded-sm px-2 py-1 font-mono text-[10px] uppercase tracking-[0.12em] text-slate-400"
                >
                  <span className="vf-dot-pulse size-1 rounded-full bg-emerald-400" aria-hidden />
                  {chip}
                </li>
              ))}
            </ul>
            {right}
          </div>
        </div>
      </header>
      {children}
      <footer className="border-t border-[#1e2b45] px-4 py-4 md:px-6">
        <p className="mx-auto w-full max-w-[1280px] font-mono text-[10px] uppercase tracking-[0.16em] text-slate-600">
          VeriFleet judge console · local InMemoryRunner session · no chat surface
        </p>
      </footer>
    </div>
  );
}
