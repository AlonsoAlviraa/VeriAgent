"use client";

import React from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { AppShell } from "@/components/shell/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useLocale } from "@/components/i18n/locale-provider";
import type { MessageKey } from "@/lib/i18n";

const FULL_HISTORY = [
  { id: 1, date: "14 Oct 2023, 10:42", issuer: "Amazon Web Services", logo: "AWS", amount: "45,20 €", status: "FIRMADO" as const },
  { id: 2, date: "12 Oct 2023, 16:15", issuer: "Restaurante El Paso", logo: "EP", amount: "120,50 €", status: "REVISAR" as const },
  { id: 3, date: "10 Oct 2023, 09:30", issuer: "PC Componentes", logo: "PC", amount: "899,00 €", status: "RECHAZADO" as const },
  { id: 4, date: "05 Oct 2023, 14:20", issuer: "Telefónica", logo: "TEL", amount: "58,90 €", status: "FIRMADO" as const },
  { id: 5, date: "01 Oct 2023, 11:00", issuer: "Iberdrola", logo: "IBE", amount: "142,30 €", status: "FIRMADO" as const },
  { id: 6, date: "28 Sep 2023, 09:15", issuer: "Repsol", logo: "REP", amount: "67,40 €", status: "FIRMADO" as const },
  { id: 7, date: "25 Sep 2023, 16:45", issuer: "Endesa", logo: "END", amount: "89,20 €", status: "REVISAR" as const },
  { id: 8, date: "20 Sep 2023, 10:30", issuer: "Naturgy", logo: "NAT", amount: "76,80 €", status: "FIRMADO" as const },
];

const STATUS_KEYS: Record<(typeof FULL_HISTORY)[number]["status"], MessageKey> = {
  FIRMADO: "history.status.FIRMADO",
  REVISAR: "history.status.REVISAR",
  RECHAZADO: "history.status.RECHAZADO",
};

const StatusBadge = ({ status }: { status: (typeof FULL_HISTORY)[number]["status"] }) => {
  const { t } = useLocale();
  const styles: Record<string, string> = {
    FIRMADO: "bg-[#eef8f1] text-[#17663f] border-[#c8e6d3]",
    REVISAR: "bg-[#fbf3e8] text-[#9a4d09] border-[#f3d5b0]",
    RECHAZADO: "bg-[#fbefee] text-[#9b2c2c] border-[#f0c7c3]",
  };

  return (
    <span className={cn("inline-flex w-fit items-center rounded-full border px-2 py-0.5 text-[11px] font-medium", styles[status])}>
      {t(STATUS_KEYS[status])}
    </span>
  );
};

export default function HistoryPage() {
  const { t } = useLocale();

  return (
    <AppShell>
      <main className="mx-auto flex w-full max-w-[1120px] flex-col gap-6 px-4 py-8 md:px-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="vf-label">{t("history.kicker")}</p>
            <h1 className="mt-2 text-[28px] font-medium tracking-[-0.03em] text-[#111]">{t("history.title")}</h1>
            <p className="mt-1 text-sm text-[#6f6e69]">
              {t("history.subtitle")}
            </p>
          </div>
          <Badge variant="outline" className="rounded-full border-[#f3d5b0] bg-[#fbf3e8] text-[#9a4d09]">
            MOCK
          </Badge>
        </div>

        <Button
          render={<Link href="/fleet" />}
          nativeButton={false}
          variant="outline"
          className="h-auto w-full justify-between rounded-lg border-[#e8e6e3] bg-white px-4 py-4 text-left hover:bg-[#fafaf8]"
        >
          <span>
            <span className="block text-sm font-medium text-[#111]">{t("history.liveTitle")}</span>
            <span className="block text-xs font-normal text-[#6f6e69]">
              {t("history.liveSub")}
            </span>
          </span>
          <ArrowRight data-icon="inline-end" className="text-[#6f6e69]" />
        </Button>

        <div className="grid grid-cols-3 gap-3">
          <div className="vf-card rounded-lg p-4">
            <p className="vf-label">{t("history.total")}</p>
            <p className="mt-2 font-mono text-2xl font-medium tabular-nums text-[#111]">{FULL_HISTORY.length}</p>
          </div>
          <div className="vf-card rounded-lg p-4">
            <p className="vf-label">{t("history.signed")}</p>
            <p className="mt-2 font-mono text-2xl font-medium tabular-nums text-[#17663f]">
              {FULL_HISTORY.filter((h) => h.status === "FIRMADO").length}
            </p>
          </div>
          <div className="vf-card rounded-lg p-4">
            <p className="vf-label">{t("history.pending")}</p>
            <p className="mt-2 font-mono text-2xl font-medium tabular-nums text-[#9a4d09]">
              {FULL_HISTORY.filter((h) => h.status === "REVISAR").length}
            </p>
          </div>
        </div>

        <section className="vf-card overflow-hidden rounded-lg">
          <div className="flex items-center justify-between border-b border-[#e8e6e3] px-4 py-3">
            <p className="text-[15px] font-medium text-[#111]">{t("history.sample")}</p>
            <span className="text-[12px] text-[#6f6e69]">{t("history.mockNote")}</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-[13px]">
              <thead>
                <tr className="border-b border-[#e8e6e3] text-[11px] font-medium tracking-wide text-[#6f6e69] uppercase">
                  <th className="px-4 py-2.5 font-medium">{t("history.date")}</th>
                  <th className="px-4 py-2.5 font-medium">{t("history.issuer")}</th>
                  <th className="px-4 py-2.5 text-right font-medium">{t("history.amount")}</th>
                  <th className="px-4 py-2.5 font-medium">{t("history.hash")}</th>
                  <th className="px-4 py-2.5 font-medium">{t("history.status")}</th>
                </tr>
              </thead>
              <tbody>
                {FULL_HISTORY.map((item) => (
                  <tr key={item.id} className="border-b border-[#e8e6e3] last:border-0">
                    <td className="px-4 py-3 text-[#6f6e69]">{item.date}</td>
                    <td className="px-4 py-3 font-medium text-[#111]">{item.issuer}</td>
                    <td className="px-4 py-3 text-right font-mono tabular-nums text-[#111]">{item.amount}</td>
                    <td className="px-4 py-3 font-mono text-[12px] text-[#6f6e69]">{item.hash}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={item.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </AppShell>
  );
}
