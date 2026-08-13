"use client";

import { AppShell } from "@/components/shell/app-shell";
import { OpenFleetCta } from "@/components/shell/open-fleet-cta";
import { useLocale } from "@/components/i18n/locale-provider";
import { cn } from "@/lib/utils";
import type { MessageKey } from "@/lib/i18n";

const TIERS: {
  name: MessageKey;
  tag: MessageKey;
  price: string;
  features: MessageKey[];
  highlight?: boolean;
}[] = [
  {
    name: "pricing.demo.name",
    tag: "pricing.demo.tag",
    price: "€0",
    features: ["pricing.demo.f1", "pricing.demo.f2", "pricing.demo.f3"],
  },
  {
    name: "pricing.issuer.name",
    tag: "pricing.issuer.tag",
    price: "€49",
    features: ["pricing.issuer.f1", "pricing.issuer.f2", "pricing.issuer.f3"],
    highlight: true,
  },
  {
    name: "pricing.ent.name",
    tag: "pricing.ent.tag",
    price: "€199",
    features: ["pricing.ent.f1", "pricing.ent.f2", "pricing.ent.f3"],
  },
];

export default function PricingPage() {
  const { t } = useLocale();

  return (
    <AppShell>
      <main className="mx-auto flex w-full max-w-[1120px] flex-col gap-6 px-4 py-8 md:px-6">
        <header className="max-w-[640px]">
          <p className="vf-label">{t("pricing.kicker")}</p>
          <h1 className="mt-2 text-[28px] font-medium tracking-[-0.03em] text-[#111]">
            {t("pricing.title")}
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-[#6f6e69]">{t("pricing.lead")}</p>
        </header>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-3 md:items-stretch">
          {TIERS.map((tier) => (
            <article
              key={tier.name}
              className={cn(
                "vf-card flex flex-col rounded-lg p-5",
                tier.highlight && "border-[#111] shadow-[0_0_0_1px_#111]"
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-[15px] font-medium tracking-tight text-[#111]">{t(tier.name)}</h2>
                <span className="rounded-full border border-[#e8e6e3] bg-[#fbfbf9] px-2 py-0.5 text-[11px] font-medium text-[#6f6e69]">
                  {t(tier.tag)}
                </span>
              </div>
              <p className="mt-4 flex items-baseline gap-1 text-[#111]">
                <span className="text-[36px] font-medium tracking-[-0.04em]">{tier.price}</span>
                {tier.price !== "€0" ? (
                  <span className="text-sm text-[#6f6e69]">{t("pricing.period")}</span>
                ) : null}
              </p>
              <ul className="mt-4 flex flex-1 flex-col gap-2">
                {tier.features.map((feature) => (
                  <li key={feature} className="flex gap-2 text-sm leading-relaxed text-[#6f6e69]">
                    <span className="mt-2 size-1.5 shrink-0 rounded-full bg-[#111]" aria-hidden />
                    {t(feature)}
                  </li>
                ))}
              </ul>
              <OpenFleetCta
                variant={tier.highlight ? "ink" : "outline"}
                className="mt-6 w-full"
              />
            </article>
          ))}
        </div>

        <p className="max-w-[640px] text-[12px] leading-relaxed text-[#6f6e69]">{t("pricing.note")}</p>
      </main>
    </AppShell>
  );
}
