"use client";

import { useLocale } from "@/components/i18n/locale-provider";

/** Honest chip: fleet ingest never calls AEAT. Never green. */
export function AeatStatusChip() {
  const { t } = useLocale();

  return (
    <span
      className="vf-chip min-h-11 cursor-default md:min-h-8"
      title={t("aeat.tooltip")}
      aria-label={`${t("aeat.chip")}. ${t("aeat.tooltip")}`}
    >
      <span className="size-1.5 shrink-0 rounded-full bg-[#cfcbc4]" aria-hidden />
      {t("aeat.chip")}
    </span>
  );
}
