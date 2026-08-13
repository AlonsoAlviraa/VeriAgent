"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useLocale } from "@/components/i18n/locale-provider";
import { LocaleToggle } from "@/components/i18n/locale-toggle";

const NAV = [
  { href: "/fleet", key: "nav.fleet" as const },
  { href: "/", key: "nav.audit" as const },
  { href: "/history", key: "nav.ledger" as const },
];

export function AppShell({
  children,
  right,
}: {
  children: React.ReactNode;
  right?: React.ReactNode;
}) {
  const path = usePathname();
  const { t } = useLocale();

  return (
    <div
      className="vf-app min-h-screen bg-[#fbfbf9] text-[#111]"
      style={{ backgroundColor: "#fbfbf9", color: "#111111" }}
    >
      <header
        className="sticky top-0 z-30 border-b border-[#e8e6e3] bg-[#fbfbf9]"
        style={{ backgroundColor: "#fbfbf9" }}
      >
        <div className="mx-auto flex w-full max-w-[1120px] items-center gap-3 px-4 py-3 md:gap-4 md:px-6">
          <Link href="/fleet" className="shrink-0 text-[15px] font-medium tracking-tight text-[#111]">
            VeriFleet
          </Link>

          <nav aria-label={t("nav.aria")} className="flex min-w-0 items-center gap-1 overflow-x-auto">
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
                  {t(item.key)}
                </Link>
              );
            })}
          </nav>

          <div className="ml-auto flex min-w-0 items-center gap-2">
            <LocaleToggle />
            <p className="hidden truncate text-[12px] text-[#6f6e69] sm:block">
              {t("nav.judgeConsole")}
            </p>
          </div>
        </div>
        {right ? <div className="mx-auto hidden max-w-[1120px] px-4 pb-3 md:block md:px-6">{right}</div> : null}
      </header>
      {children}
      <footer className="border-t border-[#e8e6e3] px-4 py-5 md:px-6">
        <p className="mx-auto w-full max-w-[1120px] text-[12px] leading-relaxed text-[#6f6e69]">
          {t("footer.identity")}
        </p>
      </footer>
    </div>
  );
}
