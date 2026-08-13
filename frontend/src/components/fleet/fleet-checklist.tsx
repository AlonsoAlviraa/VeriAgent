"use client";

import { Check } from "lucide-react";
import { useLocale } from "@/components/i18n/locale-provider";
import { cn } from "@/lib/utils";

export type ChecklistItem = { id: string; name: string; status: string; proof: string };

const REQUIRED_IDS = [
  "registry",
  "runtime",
  "memory",
  "identity",
  "gateway",
  "armor",
  "gemini",
  "adk",
  "runner",
  "aeat",
];

function isPositive(item: ChecklistItem) {
  if (item.id === "aeat") return item.status === "live";
  return item.status === "implemented" || item.status === "ok" || item.status === "live";
}

export function FleetChecklist({
  track,
  items,
  aeatRemitting,
}: {
  track?: string;
  items: ChecklistItem[];
  aeatRemitting?: boolean;
}) {
  const { t } = useLocale();
  const rows = items.length
    ? [...items].sort((a, b) => {
        const ai = REQUIRED_IDS.indexOf(a.id);
        const bi = REQUIRED_IDS.indexOf(b.id);
        if (ai === -1 && bi === -1) return 0;
        if (ai === -1) return 1;
        if (bi === -1) return -1;
        return ai - bi;
      })
    : [];

  return (
    <section aria-label={t("checklist.aria")} className="vf-card rounded-lg">
      <header className="border-b border-[#e8e6e3] px-4 py-3">
        <p className="vf-label">{t("checklist.kicker")}</p>
        <h2 className="mt-1 text-[15px] font-medium tracking-tight text-[#111]">
          {track || t("checklist.fallbackTrack")}
        </h2>
        <p className="mt-1 font-mono text-[12px] text-[#6f6e69]">
          aeat_remitting={String(aeatRemitting ?? false)} · {t("checklist.aeatOff")}
        </p>
      </header>
      {rows.length === 0 ? (
        <p className="px-4 py-3 text-[13px] leading-relaxed text-[#6f6e69]">{t("checklist.offline")}</p>
      ) : (
        <ul className="divide-y divide-[#e8e6e3]">
          {rows.map((item) => {
            const ok = isPositive(item);
            return (
              <li key={item.id || item.name} className="flex items-start gap-3 px-4 py-3">
                <span
                  className={cn(
                    "mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-full",
                    ok ? "bg-[#eef8f1] text-[#18794e]" : "bg-[#f4f3f0] text-[#cfcbc4]"
                  )}
                  aria-hidden
                >
                  {ok ? <Check className="size-2.5" strokeWidth={3} /> : (
                    <span className="size-1.5 rounded-full bg-[#cfcbc4]" />
                  )}
                </span>
                <div className="min-w-0">
                  <p className="text-[13px] text-[#111]">
                    {item.name}
                    {item.id === "aeat" ? (
                      <span className="ml-2 font-mono text-[11px] text-[#6f6e69]">false</span>
                    ) : null}
                  </p>
                  <p className="mt-0.5 text-[12px] text-[#6f6e69]">{item.proof}</p>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
