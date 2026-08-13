"use client";

import Link from "next/link";
import { AppShell } from "@/components/shell/app-shell";
import { OpenFleetCta } from "@/components/shell/open-fleet-cta";
import { useLocale } from "@/components/i18n/locale-provider";
import type { MessageKey } from "@/lib/i18n";

const OFFICIAL_LINKS: { href: string; key: MessageKey }[] = [
  { href: "https://www.sede.fnmt.gob.es/", key: "tutorial.step1.fnmt" },
  {
    href: "https://www.sede.fnmt.gob.es/preguntas-frecuentes/certificado-de-persona-fisica/-/asset_publisher/eIal9z2VE0Kb/content/certificados-electr%C3%B3nicos-v%C3%A1lidos-para-el-sistema-veri*factu",
    key: "tutorial.step1.verifactu",
  },
  {
    href: "https://sede.agenciatributaria.gob.es/Sede/ayuda/consultas-informaticas/firma-digital-sistema-clave-pin-tecnica/informacion-pasos-obtencion-certificado-electronico.html",
    key: "tutorial.step1.aeat",
  },
  { href: "https://sede.agenciatributaria.gob.es/", key: "tutorial.step1.sede" },
];

const STEPS: { title: MessageKey; body: MessageKey }[] = [
  { title: "tutorial.step1.title", body: "tutorial.step1.body" },
  { title: "tutorial.step2.title", body: "tutorial.step2.body" },
  { title: "tutorial.step3.title", body: "tutorial.step3.body" },
  { title: "tutorial.step4.title", body: "tutorial.step4.body" },
  { title: "tutorial.step5.title", body: "tutorial.step5.body" },
  { title: "tutorial.step6.title", body: "tutorial.step6.body" },
];

const NEVER: MessageKey[] = [
  "tutorial.never1",
  "tutorial.never2",
  "tutorial.never3",
  "tutorial.never4",
];

const ENV_SAMPLE = `AEAT_CERT_PATH=/var/lib/verifleet/aeat-cert.pem
AEAT_KEY_PATH=/var/lib/verifleet/aeat-key.pem
AEAT_ENV=SANDBOX`;

export default function TutorialPage() {
  const { t } = useLocale();

  return (
    <AppShell>
      <main className="mx-auto flex w-full max-w-[720px] flex-col gap-6 px-4 py-10 md:px-6 md:py-14">
        <header>
          <p className="vf-label">{t("tutorial.kicker")}</p>
          <h1 className="vf-prose-hero mt-3 text-[32px] md:text-[40px]">{t("tutorial.title")}</h1>
          <p className="mt-4 text-[16px] leading-relaxed text-[#6f6e69]">{t("tutorial.lead")}</p>
        </header>

        <aside className="vf-card rounded-lg border-[#e8e6e3] bg-white p-4">
          <p className="text-sm font-medium text-[#111]">{t("tutorial.warnTitle")}</p>
          <p className="mt-1 text-sm leading-relaxed text-[#6f6e69]">{t("tutorial.warnBody")}</p>
        </aside>

        <ol className="flex flex-col gap-3">
          {STEPS.map((step, index) => (
            <li key={step.title} className="vf-card rounded-lg p-4 sm:p-5">
              <div className="flex gap-3">
                <span
                  className="mt-0.5 inline-flex size-7 shrink-0 items-center justify-center rounded-full border border-[#e8e6e3] bg-[#fbfbf9] text-[12px] font-medium text-[#111]"
                  aria-hidden
                >
                  {index + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <h2 className="text-[15px] font-medium tracking-tight text-[#111]">{t(step.title)}</h2>
                  <p className="mt-1 text-sm leading-relaxed text-[#6f6e69]">{t(step.body)}</p>

                  {index === 0 ? (
                    <ul className="mt-3 flex flex-col gap-2">
                      {OFFICIAL_LINKS.map((link) => (
                        <li key={link.href}>
                          <Link
                            href={link.href}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-[#185fa5] underline-offset-2 hover:underline"
                          >
                            {t(link.key)}
                          </Link>
                        </li>
                      ))}
                    </ul>
                  ) : null}

                  {index === 2 ? (
                    <div className="mt-3">
                      <pre className="overflow-x-auto rounded-md border border-[#e8e6e3] bg-[#fbfbf9] p-3 font-mono text-[12px] leading-relaxed text-[#111]">
                        {ENV_SAMPLE}
                      </pre>
                      <p className="mt-2 text-[12px] text-[#6f6e69]">{t("tutorial.envHint")}</p>
                    </div>
                  ) : null}
                </div>
              </div>
            </li>
          ))}
        </ol>

        <section className="vf-card rounded-lg p-4 sm:p-5">
          <h2 className="text-[15px] font-medium tracking-tight text-[#111]">{t("tutorial.neverTitle")}</h2>
          <ul className="mt-3 flex flex-col gap-2">
            {NEVER.map((key) => (
              <li key={key} className="flex gap-2 text-sm leading-relaxed text-[#6f6e69]">
                <span className="mt-2 size-1.5 shrink-0 rounded-full bg-[#cfcbc4]" aria-hidden />
                {t(key)}
              </li>
            ))}
          </ul>
        </section>

        <OpenFleetCta className="w-full sm:w-auto" />
      </main>
    </AppShell>
  );
}
