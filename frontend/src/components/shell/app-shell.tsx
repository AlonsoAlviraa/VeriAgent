"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ShieldCheck } from "lucide-react";
import { cn } from "@/lib/cn";

const NAV = [
  { href: "/fleet", label: "Fleet" },
  { href: "/", label: "Audit" },
  { href: "/history", label: "Ledger" },
];

export function BrandMark({ size = "md" }: { size?: "sm" | "md" }) {
  const box = size === "sm" ? "h-8 w-8" : "h-9 w-9";
  return (
    <span
      className={cn(
        "relative inline-flex items-center justify-center rounded-xl bg-gradient-to-br from-emerald-300 via-emerald-500 to-teal-700 shadow-[0_0_24px_rgba(52,211,153,0.35)]",
        box
      )}
    >
      <ShieldCheck className={cn("text-[#06110c]", size === "sm" ? "h-4 w-4" : "h-5 w-5")} />
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
    <div className="vf-app relative min-h-screen text-slate-100">
      <div className="vf-aurora" aria-hidden />
      <header className="sticky top-0 z-30 border-b border-white/8 bg-[#07090f]/70 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-3 sm:px-8">
          <div className="flex min-w-0 items-center gap-4">
            <Link href="/fleet" className="flex items-center gap-2.5">
              <BrandMark />
              <span className="leading-tight">
                <span className="block text-[15px] font-semibold tracking-tight text-white">
                  VeriFleet
                </span>
                <span className="hidden text-[10px] uppercase tracking-[0.22em] text-emerald-300/80 sm:block">
                  Fortified Enterprise Fleet
                </span>
              </span>
            </Link>
            <nav className="hidden items-center gap-1 rounded-full border border-white/8 bg-white/4 p-1 md:flex">
              {NAV.map((item) => {
                const active = item.href === "/" ? path === "/" : path.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "rounded-full px-3 py-1 text-xs font-medium transition",
                      active
                        ? "bg-white/10 text-white shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08)]"
                        : "text-slate-400 hover:text-white"
                    )}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>
          <div className="flex shrink-0 items-center gap-2 sm:gap-3">
            <span className="hidden items-center gap-1.5 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-emerald-300 lg:inline-flex">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
              ATA 2026
            </span>
            {right}
          </div>
        </div>
      </header>
      {children}
    </div>
  );
}
