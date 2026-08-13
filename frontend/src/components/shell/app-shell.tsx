"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/fleet", label: "Fleet" },
  { href: "/", label: "Audit" },
  { href: "/history", label: "Ledger" },
];

export function BrandMark({ size = "md" }: { size?: "sm" | "md" }) {
  const box = size === "sm" ? "size-8" : "size-9";
  return (
    <span
      className={cn(
        "relative inline-flex items-center justify-center rounded-xl bg-gradient-to-br from-emerald-300 via-emerald-500 to-teal-700 shadow-[0_0_24px_rgba(52,211,153,0.35)]",
        box
      )}
    >
      <ShieldCheck className={cn("text-[#06110c]", size === "sm" ? "size-4" : "size-5")} />
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
      <header className="sticky top-0 z-30 border-b border-white/8 bg-[#07090f]/78 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl flex-col gap-2 px-4 py-2.5 sm:px-8">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3 sm:gap-4">
              <Link href="/fleet" className="flex min-w-0 items-center gap-2.5">
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
              <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-emerald-300">
                <span className="vf-live-dot size-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]" />
                ATA 2026
              </span>
              {right}
            </div>
          </div>
          <nav className="flex items-center gap-1 overflow-x-auto rounded-full border border-white/8 bg-white/4 p-1 md:hidden">
            {NAV.map((item) => {
              const active = item.href === "/" ? path === "/" : path.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "min-w-0 flex-1 rounded-full px-3 py-1.5 text-center text-xs font-medium transition",
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
      </header>
      {children}
    </div>
  );
}
