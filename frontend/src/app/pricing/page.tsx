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

const FAQS: { q: MessageKey; a: MessageKey }[] = [
  { q: "pricing.faq1.q", a: "pricing.faq1.a" },
  { q: "pricing.faq2.q", a: "pricing.faq2.a" },
  { q: "pricing.faq3.q", a: "pricing.faq3.a" },
];

export default function PricingPage() {
  const { t } = useLocale();

  return (
    <AppShell>
      <main className="mx-auto flex w-full max-w-[1120px] flex-col gap-10 px-4 py-10 md:px-6 md:py-14">
        <header className="max-w-[640px]">
          <p className="vf-label">{t("pricing.kicker")}</p>
          <h1 className="vf-prose-hero mt-3 text-[32px] md:text-[40px]">{t("pricing.title")}</h1>
          <p className="mt-4 text-[16px] leading-relaxed text-[#6f6e69]">{t("pricing.lead")}</p>
          <p className="mt-3 text-[12px] uppercase tracking-[0.04em] text-[#6f6e69]">{t("pricing.billed")}</p>
        </header>

        <div className="grid grid-cols-1 items-stretch gap-3 md:grid-cols-3">
          {TIERS.map((tier) => (
            <article
              key={tier.name}
              className={cn(
                "vf-card flex flex-col rounded-lg p-5 md:p-6",
                tier.highlight && "border-[#111] md:py-8 shadow-[0_0_0_1px_#111]"
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-[15px] font-medium tracking-tight text-[#111]">{t(tier.name)}</h2>
                <span
                  className={cn(
                    "rounded-full border px-2 py-0.5 text-[11px] font-medium",
                    tier.highlight
                      ? "border-[#111] bg-[#111] text-white"
                      : "border-[#e8e6e3] bg-[#fbfbf9] text-[#6f6e69]"
                  )}
                >
                  {t(tier.tag)}
                </span>
              </div>
              <p className="mt-5 flex items-baseline gap-1 text-[#111]">
                <span className="text-[40px] font-medium tracking-[-0.04em]">{tier.price}</span>
                {tier.price !== "€0" ? (
                  <span className="text-sm text-[#6f6e69]">{t("pricing.period")}</span>
                ) : null}
              </p>
              <ul className="mt-5 flex flex-1 flex-col gap-2.5">
                {tier.features.map((feature) => (
                  <li key={feature} className="flex gap-2 text-sm leading-relaxed text-[#6f6e69]">
                    <span
                      className={cn(
                        "mt-2 size-1.5 shrink-0 rounded-full",
                        tier.highlight ? "bg-[#111]" : "bg-[#cfcbc4]"
                      )}
                      aria-hidden
                    />
                    {t(feature)}
                  </li>
                ))}
              </ul>
              <OpenFleetCta variant={tier.highlight ? "ink" : "outline"} className="mt-7 w-full" />
            </article>
          ))}
        </div>

        <p className="max-w-[640px] text-[12px] leading-relaxed text-[#6f6e69]">{t("pricing.note")}</p>

        <section className="max-w-[720px]">
          <h2 className="text-[15px] font-medium tracking-tight text-[#111]">{t("pricing.faqTitle")}</h2>
          <div className="mt-4 flex flex-col gap-3">
            {FAQS.map((faq) => (
              <details key={faq.q} className="vf-card group rounded-lg px-4 py-3">
                <summary className="flex cursor-pointer list-none items-start justify-between gap-3 text-[14px] font-medium text-[#111] marker:content-none [&::-webkit-details-marker]:hidden">
                  <span>{t(faq.q)}</span>
                  <span className="shrink-0 text-[#cfcbc4] group-open:hidden" aria-hidden>
                    +
                  </span>
                  <span className="hidden shrink-0 text-[#cfcbc4] group-open:inline" aria-hidden>
                    –
                  </span>
                </summary>
                <p className="mt-2 text-sm leading-relaxed text-[#6f6e69]">{t(faq.a)}</p>
              </details>
            ))}
          </div>
        </section>
      </main>
    </AppShell>
  );
}
