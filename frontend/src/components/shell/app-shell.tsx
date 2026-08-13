"use client";

import { useEffect, useId, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useLocale } from "@/components/i18n/locale-provider";
import { LocaleToggle } from "@/components/i18n/locale-toggle";
import type { MessageKey } from "@/lib/i18n";

const PRIMARY: { href: string; key: MessageKey }[] = [
  { href: "/fleet", key: "nav.fleet" },
  { href: "/", key: "nav.audit" },
  { href: "/history", key: "nav.ledger" },
];

const SECONDARY: { href: string; key: MessageKey }[] = [
  { href: "/tutorial", key: "nav.tutorial" },
  { href: "/security", key: "nav.security" },
  { href: "/pricing", key: "nav.pricing" },
];

function isActive(path: string, href: string) {
  if (href === "/") return path === "/";
  if (href === "/tutorial") return path.startsWith("/tutorial") || path.startsWith("/setup");
  return path.startsWith(href);
}

function NavLink({
  href,
  label,
  active,
}: {
  href: string;
  label: string;
  active: boolean;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "shrink-0 rounded-md px-2.5 py-1 text-[13px] transition-colors duration-150",
        active ? "bg-white text-[#111] shadow-[0_0_0_1px_#e8e6e3]" : "text-[#6f6e69] hover:text-[#111]"
      )}
    >
      {label}
    </Link>
  );
}

function MoreNav({ path }: { path: string }) {
  const { t } = useLocale();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const menuId = useId();
  const anyActive = SECONDARY.some((item) => isActive(path, item.href));

  useEffect(() => {
    setOpen(false);
  }, [path]);

  useEffect(() => {
    if (!open) return;
    const onPointer = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={rootRef} className="relative sm:hidden">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={menuId}
        aria-haspopup="menu"
        onClick={() => setOpen((value) => !value)}
        className={cn(
          "shrink-0 rounded-md px-2.5 py-1 text-[13px] transition-colors duration-150",
          anyActive || open
            ? "bg-white text-[#111] shadow-[0_0_0_1px_#e8e6e3]"
            : "text-[#6f6e69] hover:text-[#111]"
        )}
      >
        {t("nav.more")}
      </button>
      {open ? (
        <div
          id={menuId}
          role="menu"
          className="absolute left-0 top-[calc(100%+6px)] z-40 min-w-[168px] rounded-lg border border-[#e8e6e3] bg-white p-1 shadow-[0_8px_24px_rgba(17,17,17,0.06)]"
        >
          {SECONDARY.map((item) => {
            const active = isActive(path, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                role="menuitem"
                className={cn(
                  "block rounded-md px-2.5 py-2 text-[13px]",
                  active ? "bg-[#fbfbf9] text-[#111]" : "text-[#6f6e69] hover:text-[#111]"
                )}
              >
                {t(item.key)}
              </Link>
            );
          })}
        </div>
      ) : null}
    </div>
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
        <div className="mx-auto flex w-full max-w-[1120px] items-center gap-2 px-4 py-3 md:gap-4 md:px-6">
          <Link href="/fleet" className="shrink-0 text-[15px] font-medium tracking-tight text-[#111]">
            VeriFleet
          </Link>

          <nav aria-label={t("nav.aria")} className="flex min-w-0 items-center gap-1 overflow-x-auto">
            {PRIMARY.map((item) => (
              <NavLink
                key={item.href}
                href={item.href}
                label={t(item.key)}
                active={isActive(path, item.href)}
              />
            ))}
            <MoreNav path={path} />
            <div className="hidden items-center gap-1 sm:flex">
              {SECONDARY.map((item) => (
                <NavLink
                  key={item.href}
                  href={item.href}
                  label={t(item.key)}
                  active={isActive(path, item.href)}
                />
              ))}
            </div>
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
