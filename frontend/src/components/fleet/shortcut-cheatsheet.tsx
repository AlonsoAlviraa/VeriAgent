"use client";

import { useEffect, useRef } from "react";
import { useLocale } from "@/components/i18n/locale-provider";
import type { MessageKey } from "@/lib/i18n";

const ROWS: { key: string; label: MessageKey }[] = [
  { key: "1", label: "shortcuts.1" },
  { key: "2", label: "shortcuts.2" },
  { key: "3", label: "shortcuts.3" },
  { key: "4", label: "shortcuts.4" },
  { key: "u", label: "shortcuts.u" },
  { key: "g", label: "shortcuts.g" },
  { key: "?", label: "shortcuts.help" },
];

export function ShortcutCheatsheet({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const { t } = useLocale();
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    closeRef.current?.focus();
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="vf-no-print fixed inset-0 z-50 flex items-end justify-center bg-[#111111]/40 p-4 sm:items-center"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="fleet-shortcuts-title"
        className="w-full max-w-[390px] rounded-lg border border-[#e8e6e3] bg-white p-4 shadow-[0_8px_24px_rgba(17,17,17,0.08)]"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <h2 id="fleet-shortcuts-title" className="text-[15px] font-medium tracking-tight text-[#111]">
            {t("shortcuts.title")}
          </h2>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            className="min-h-11 min-w-11 rounded-md text-[13px] text-[#6f6e69] hover:text-[#111] sm:min-h-8 sm:min-w-8"
          >
            {t("shortcuts.close")}
          </button>
        </div>
        <ul className="mt-3 divide-y divide-[#e8e6e3]">
          {ROWS.map((row) => (
            <li key={row.key} className="flex items-center justify-between gap-3 py-2.5">
              <span className="text-[13px] text-[#111]">{t(row.label)}</span>
              <kbd className="rounded border border-[#e8e6e3] bg-[#fbfbf9] px-1.5 py-0.5 font-mono text-[12px] text-[#6f6e69]">
                {row.key}
              </kbd>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
