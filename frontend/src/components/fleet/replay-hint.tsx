"use client";

import { useLocale } from "@/components/i18n/locale-provider";

export function ReplayHint() {
  const { t } = useLocale();
  return (
    <p className="text-[12px] leading-relaxed text-[#6f6e69]">
      {t("replay.prefix")}{" "}
      <code className="font-mono text-[11px] text-[#111]">pytest tests/test_fleet_adk.py</code>
      {" · "}
      {t("replay.fixturesIn")} <code className="font-mono text-[11px] text-[#111]">/demo-fixtures</code>
    </p>
  );
}
