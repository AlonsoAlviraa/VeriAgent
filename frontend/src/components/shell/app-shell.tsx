"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/fleet", label: "Fleet" },
  { href: "/", label: "Audit" },
  { href: "/history", label: "Ledger" },
];

export function AppShell({
  children,
  right,
}: {
  children: React.ReactNode;
  right?: React.ReactNode;
}) {
  const path = usePathname();

  return (
    <div className="vf-app min-h-screen bg-[#fafaf8] text-[#111]">
      <header className="sticky top-0 z-30 border-b border-[#e8e6e3] bg-[#fafaf8]/90 backdrop-blur-sm">
        <div className="mx-auto flex w-full max-w-[1120px] items-center gap-4 px-4 py-3 md:px-6">
          <Link href="/fleet" className="shrink-0 text-[15px] font-medium tracking-tight text-[#111]">
            VeriFleet
          </Link>

          <nav aria-label="Console sections" className="flex min-w-0 items-center gap-1 overflow-x-auto">
            {NAV.map((item) => {
              const active = item.href === "/" ? path === "/" : path.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "shrink-0 rounded-md px-2.5 py-1 text-[13px] transition-colors duration-150",
                    active
                      ? "bg-white text-[#111] shadow-[0_0_0_1px_#e8e6e3]"
                      : "text-[#6f6e69] hover:text-[#111]"
                  )}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <p className="ml-auto hidden truncate text-[12px] text-[#6f6e69] sm:block">
            google-adk · gemini-3.5-flash
          </p>
        </div>
        {right ? <div className="mx-auto hidden max-w-[1120px] px-4 pb-3 md:block md:px-6">{right}</div> : null}
      </header>
      {children}
      <footer className="border-t border-[#e8e6e3] px-4 py-5 md:px-6">
        <p className="mx-auto w-full max-w-[1120px] text-[12px] leading-relaxed text-[#6f6e69]">
          VeriFleet · google-adk · gemini-3.5-flash · local InMemoryRunner session · no chat surface
        </p>
      </footer>
    </div>
  );
}
