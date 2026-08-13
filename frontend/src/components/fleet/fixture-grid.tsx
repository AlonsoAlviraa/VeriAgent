"use client";

import { ArrowRight, Bug, Calculator, FileCheck2, UtensilsCrossed, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { useLocale } from "@/components/i18n/locale-provider";
import type { MessageKey } from "@/lib/i18n";

export const FIXTURES = [
  {
    id: "valid",
    labelKey: "fixtures.valid" as const satisfies MessageKey,
    hintKey: "fixtures.validHint" as const satisfies MessageKey,
    jobKey: "fixtures.job.valid" as const satisfies MessageKey,
    path: "/demo-fixtures/valid_invoice.json",
    expect: "SIGNED" as const,
    icon: FileCheck2,
  },
  {
    id: "math",
    labelKey: "fixtures.math" as const satisfies MessageKey,
    hintKey: "fixtures.mathHint" as const satisfies MessageKey,
    jobKey: "fixtures.job.math" as const satisfies MessageKey,
    path: "/demo-fixtures/math_error.json",
    expect: "ESCALATED" as const,
    icon: Calculator,
  },
  {
    id: "injection",
    labelKey: "fixtures.injection" as const satisfies MessageKey,
    hintKey: "fixtures.injectionHint" as const satisfies MessageKey,
    jobKey: "fixtures.job.injection" as const satisfies MessageKey,
    path: "/demo-fixtures/injection.json",
    expect: "BLOCKED" as const,
    icon: Bug,
  },
  {
    id: "hospitality",
    labelKey: "fixtures.hospitality" as const satisfies MessageKey,
    hintKey: "fixtures.hospitalityHint" as const satisfies MessageKey,
    jobKey: "fixtures.job.hospitality" as const satisfies MessageKey,
    path: "/demo-fixtures/hospitality.json",
    expect: "ESCALATED" as const,
    icon: UtensilsCrossed,
  },
];

export function FixtureGrid({
  busy,
  activeJob,
  onDispatch,
}: {
  busy: boolean;
  activeJob: string;
  onDispatch: (path: string) => void;
}) {
  const { t } = useLocale();

  return (
    <section aria-label={t("fixtures.aria")} className="flex flex-col gap-3">
      <h2 className="text-[15px] font-medium tracking-tight text-[#111]">{t("fixtures.heading")}</h2>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {FIXTURES.map((fixture, index) => {
          const Icon = fixture.icon;
          const active = busy && activeJob === fixture.path;
          return (
            <Card
              key={fixture.id}
              size="sm"
              className="vf-card gap-0 rounded-lg p-4 ring-0 transition-transform duration-150 hover:-translate-y-0.5"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="vf-label">{t(fixture.jobKey)}</p>
                  <h3 className="mt-1 text-[15px] leading-tight font-medium text-[#111]">
                    {t(fixture.labelKey)}
                  </h3>
                  <p className="mt-1 text-[12px] text-[#6f6e69]">
                    {fixture.expect}
                    <kbd className="ml-2 rounded border border-[#e8e6e3] bg-[#fbfbf9] px-1.5 font-mono text-[11px] text-[#6f6e69]">
                      {index + 1}
                    </kbd>
                  </p>
                </div>
                {active ? (
                  <Loader2 className="size-4 shrink-0 animate-spin text-[#6f6e69]" />
                ) : (
                  <Icon className="size-4 shrink-0 text-[#6f6e69]" />
                )}
              </div>
              <p className="mt-2 text-[13px] leading-snug text-[#6f6e69]">{t(fixture.hintKey)}</p>
              <Button
                size="sm"
                disabled={busy}
                onClick={() => onDispatch(fixture.path)}
                className={cn(
                  "mt-4 h-10 w-full justify-center rounded-md bg-[#111] text-[12px] font-medium tracking-[0.12em] text-white uppercase transition-colors duration-150 sm:h-9",
                  "hover:bg-emerald-400 hover:text-[#04180f]",
                  "focus-visible:bg-emerald-400 focus-visible:text-[#04180f]"
                )}
              >
                {t("fixtures.dispatch")}
                <ArrowRight data-icon="inline-end" aria-hidden />
              </Button>
            </Card>
          );
        })}
      </div>
    </section>
  );
}
