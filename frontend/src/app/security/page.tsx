"use client";

import { ArrowRight } from "lucide-react";
import { AppShell } from "@/components/shell/app-shell";
import { OpenFleetCta } from "@/components/shell/open-fleet-cta";
import { useLocale } from "@/components/i18n/locale-provider";
import type { MessageKey } from "@/lib/i18n";

const CONTROLS: { title: MessageKey; body: MessageKey }[] = [
  { title: "security.c1.title", body: "security.c1.body" },
  { title: "security.c2.title", body: "security.c2.body" },
  { title: "security.c3.title", body: "security.c3.body" },
  { title: "security.c5.title", body: "security.c5.body" },
];

const ARCH: { title: MessageKey; sub: MessageKey }[] = [
  { title: "security.archIngest", sub: "security.archIngestSub" },
  { title: "security.archConsult", sub: "security.archConsultSub" },
  { title: "security.archHash", sub: "security.archHashSub" },
];

export default function SecurityPage() {
  const { t } = useLocale();

  return (
    <AppShell>
      <main className="mx-auto flex w-full max-w-[800px] flex-col gap-8 px-4 py-10 md:px-6 md:py-14">
        <header>
          <p className="vf-label">{t("security.kicker")}</p>
          <h1 className="vf-prose-hero mt-3 text-[32px] md:text-[40px]">{t("security.title")}</h1>
          <p className="mt-4 text-[16px] leading-relaxed text-[#6f6e69]">{t("security.lead")}</p>
        </header>

        <p className="max-w-[640px] text-[15px] leading-relaxed text-[#111]">{t("security.manifesto")}</p>

        <ol className="flex flex-col gap-3">
          {CONTROLS.map((control, index) => (
            <li key={control.title} className="vf-card flex gap-4 rounded-lg p-4 sm:p-5">
              <span
                className="mt-0.5 inline-flex size-7 shrink-0 items-center justify-center rounded-full border border-[#e8e6e3] bg-[#fbfbf9] text-[12px] font-medium text-[#111]"
                aria-hidden
              >
                {index + 1}
              </span>
              <div className="min-w-0">
                <h2 className="text-[15px] font-medium tracking-tight text-[#111]">{t(control.title)}</h2>
                <p className="mt-1 text-sm leading-relaxed text-[#6f6e69]">{t(control.body)}</p>
              </div>
            </li>
          ))}
        </ol>

        <section className="vf-card rounded-lg p-4 sm:p-5">
          <p className="vf-label">{t("security.archTitle")}</p>
          <ol className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-stretch">
            {ARCH.map((step, index) => (
              <li key={step.title} className="flex min-w-0 flex-1 items-stretch gap-3">
                <div className="min-w-0 flex-1 rounded-lg border border-[#e8e6e3] bg-[#fbfbf9] p-3">
                  <p className="text-[13px] font-medium text-[#111]">{t(step.title)}</p>
                  <p className="mt-0.5 text-[12px] text-[#6f6e69]">{t(step.sub)}</p>
                </div>
                {index < ARCH.length - 1 ? (
                  <ArrowRight className="mt-4 hidden size-4 shrink-0 text-[#cfcbc4] sm:block" aria-hidden />
                ) : null}
              </li>
            ))}
          </ol>
        </section>

        <p className="text-sm leading-relaxed text-[#6f6e69]">{t("security.c6.body")}</p>

        <OpenFleetCta className="w-full sm:w-auto" />
      </main>
    </AppShell>
  );
}
