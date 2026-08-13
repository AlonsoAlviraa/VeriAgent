"use client";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { asVerdict, verdictStyles, type Verdict } from "./verdict";
import { useLocale } from "@/components/i18n/locale-provider";
import type { MessageKey } from "@/lib/i18n";

const HINT_KEYS: Record<Verdict, MessageKey> = {
  SIGNED: "verdict.hint.SIGNED",
  ESCALATED: "verdict.hint.ESCALATED",
  BLOCKED: "verdict.hint.BLOCKED",
};

export function VerdictPill({ verdict }: { verdict?: string }) {
  const { locale, t } = useLocale();
  const key: Verdict = asVerdict(verdict);
  const s = verdictStyles[key];
  const token = verdict || key;
  return (
    <Badge
      variant="outline"
      className={cn(
        "h-auto rounded-md border px-2 py-0.5 text-[11px] font-medium tracking-normal",
        s.border,
        s.bg,
        s.text
      )}
    >
      {token}
      {locale === "es" ? (
        <span className="ml-1 font-normal opacity-70">· {t(HINT_KEYS[key])}</span>
      ) : null}
    </Badge>
  );
}

export function shortHash(hash: string) {
  if (hash.length <= 20) return hash;
  return `${hash.slice(0, 8)}…${hash.slice(-8)}`;
}
