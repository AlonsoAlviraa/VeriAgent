"use client";

import React from "react";
import Link from "next/link";
import { CheckCircle2, AlertTriangle, XCircle, Download, ExternalLink, ArrowRight } from "lucide-react";
import { AppShell } from "@/components/shell/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const FULL_HISTORY = [
  { id: 1, date: "14 Oct 2023, 10:42", issuer: "Amazon Web Services", logo: "AWS", amount: "45,20 €", status: "FIRMADO", hash: "XJ9K2M..." },
  { id: 2, date: "12 Oct 2023, 16:15", issuer: "Restaurante El Paso", logo: "EP", amount: "120,50 €", status: "REVISAR", hash: "P8Q2L1..." },
  { id: 3, date: "10 Oct 2023, 09:30", issuer: "PC Componentes", logo: "PC", amount: "899,00 €", status: "RECHAZADO", hash: "T5R3K9..." },
  { id: 4, date: "05 Oct 2023, 14:20", issuer: "Telefónica", logo: "TEL", amount: "58,90 €", status: "FIRMADO", hash: "M7V4P2..." },
  { id: 5, date: "01 Oct 2023, 11:00", issuer: "Iberdrola", logo: "IBE", amount: "142,30 €", status: "FIRMADO", hash: "H2N8L5..." },
  { id: 6, date: "28 Sep 2023, 09:15", issuer: "Repsol", logo: "REP", amount: "67,40 €", status: "FIRMADO", hash: "W1Q6R8..." },
  { id: 7, date: "25 Sep 2023, 16:45", issuer: "Endesa", logo: "END", amount: "89,20 €", status: "REVISAR", hash: "U9T5V3..." },
  { id: 8, date: "20 Sep 2023, 10:30", issuer: "Naturgy", logo: "NAT", amount: "76,80 €", status: "FIRMADO", hash: "K4P1M7..." },
];

const StatusBadge = ({ status }: { status: string }) => {
  const styles: Record<string, string> = {
    FIRMADO: "bg-emerald-400/12 text-emerald-300 ring-1 ring-emerald-400/25",
    REVISAR: "bg-amber-400/12 text-amber-200 ring-1 ring-amber-400/25",
    RECHAZADO: "bg-rose-400/12 text-rose-300 ring-1 ring-rose-400/25",
  };

  return (
    <span className={cn("inline-flex w-fit items-center gap-1 rounded-full px-2 py-1 text-[10px] font-bold", styles[status])}>
      {status === "FIRMADO" && <CheckCircle2 className="size-3" />}
      {status === "REVISAR" && <AlertTriangle className="size-3" />}
      {status === "RECHAZADO" && <XCircle className="size-3" />}
      {status}
    </span>
  );
};

export default function HistoryPage() {
  return (
    <AppShell>
      <main className="relative z-10 mx-auto flex max-w-6xl flex-col gap-8 px-4 py-8 sm:px-8 sm:py-10">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="vf-kicker">Product ledger</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white">Ledger</h1>
            <p className="mt-1 text-sm text-slate-500">
              Mock Smart Audit rows. Not live evidence. Live fleet decisions are on /fleet.
            </p>
          </div>
          <Badge variant="outline" className="border-amber-400/30 bg-amber-400/10 text-amber-100">
            MOCK
          </Badge>
        </div>

        <Button
          render={<Link href="/fleet" />}
          nativeButton={false}
          variant="ghost"
          className="vf-card vf-card-hover h-auto w-full justify-between rounded-2xl px-5 py-4 text-left"
        >
          <span>
            <span className="block text-sm font-semibold text-white">Live SIGN / ESCALATE / BLOCK runs</span>
            <span className="block text-xs font-normal text-slate-500">
              This table is a product mock. The contest console is /fleet.
            </span>
          </span>
          <ArrowRight data-icon="inline-end" className="text-emerald-300" />
        </Button>

        <div className="vf-stagger grid grid-cols-3 gap-3">
          <div className="vf-card rounded-2xl p-5">
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Total</p>
            <p className="mt-2 text-3xl font-semibold text-white">{FULL_HISTORY.length}</p>
            <p className="mt-1 text-[10px] uppercase tracking-[0.14em] text-slate-600">mock</p>
          </div>
          <div className="vf-card rounded-2xl p-5 ring-1 ring-emerald-400/15">
            <p className="text-[10px] font-bold uppercase tracking-widest text-emerald-300/80">Signed</p>
            <p className="mt-2 text-3xl font-semibold text-emerald-300">
              {FULL_HISTORY.filter((h) => h.status === "FIRMADO").length}
            </p>
            <p className="mt-1 text-[10px] uppercase tracking-[0.14em] text-slate-600">mock</p>
          </div>
          <div className="vf-card rounded-2xl p-5 ring-1 ring-amber-400/15">
            <p className="text-[10px] font-bold uppercase tracking-widest text-amber-200/80">Pending</p>
            <p className="mt-2 text-3xl font-semibold text-amber-200">
              {FULL_HISTORY.filter((h) => h.status === "REVISAR").length}
            </p>
            <p className="mt-1 text-[10px] uppercase tracking-[0.14em] text-slate-600">mock</p>
          </div>
        </div>

        <section className="vf-card overflow-hidden rounded-[2rem]">
          <div className="flex items-center justify-between border-b border-white/6 px-5 py-3">
            <p className="text-xs font-semibold text-slate-300">Sample rows</p>
            <Badge variant="outline" className="text-[10px] text-amber-100">
              MOCK — not live evidence
            </Badge>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-white/6 text-[11px] font-bold uppercase tracking-widest text-slate-500">
                  <th className="px-6 py-4">Date</th>
                  <th className="px-2 py-4">Issuer</th>
                  <th className="px-2 py-4 text-right">Amount</th>
                  <th className="px-2 py-4">Hash</th>
                  <th className="px-2 py-4">Status</th>
                  <th className="px-6 py-4" />
                </tr>
              </thead>
              <tbody className="divide-y divide-white/6">
                {FULL_HISTORY.map((item) => (
                  <tr key={item.id} className="transition hover:bg-white/3">
                    <td className="px-6 py-4 text-sm text-slate-500">{item.date}</td>
                    <td className="px-2 py-4">
                      <div className="flex items-center gap-3">
                        <div className="flex size-10 items-center justify-center rounded-lg bg-white/6 text-[10px] font-black text-white">
                          {item.logo}
                        </div>
                        <span className="text-sm font-semibold text-slate-200">{item.issuer}</span>
                      </div>
                    </td>
                    <td className="px-2 py-4 text-right font-mono text-sm font-semibold text-white">{item.amount}</td>
                    <td className="px-2 py-4 font-mono text-xs text-slate-500">{item.hash}</td>
                    <td className="px-2 py-4">
                      <StatusBadge status={item.status} />
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-end gap-1 text-slate-500">
                        <span className="rounded-lg p-2">
                          <ExternalLink className="size-4" />
                        </span>
                        <span className="rounded-lg p-2">
                          <Download className="size-4" />
                        </span>
                      </div>
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
