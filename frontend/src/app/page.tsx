"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  FileUp,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Loader2,
  ArrowRight,
  Lock,
  Scale,
  ShieldOff,
} from "lucide-react";
import { StatusBadge } from "@/components/ui/status-badge";
import { CSVDisplay } from "@/components/ui/csv-display";
import { OrgSwitcher, ChainIntegrityBadgeLive } from "@/components/org/org-switcher";
import { useInvoiceStatus } from "@/hooks/use-invoice";
import apiClient from "@/lib/api-client";
import { InvoiceStatus } from "@/lib/types/api";
import { AppShell } from "@/components/shell/app-shell";
import { cn } from "@/lib/cn";

export default function SmartAuditDashboard() {
  const [file, setFile] = useState<File | null>(null);
  const [invoiceId, setInvoiceId] = useState<string | null>(null);
  const [tenantId, setTenantId] = useState<string>("default");
  const [uploadStatus, setUploadStatus] = useState<"IDLE" | "UPLOADING" | "PROCESSING" | "SUCCESS" | "ERROR">("IDLE");
  const [errorMsg, setErrorMsg] = useState("");

  const { data: auditData } = useInvoiceStatus(invoiceId);

  const onFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;

    setFile(selectedFile);
    setUploadStatus("UPLOADING");
    setErrorMsg("");

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const uploadRes = await apiClient.post<{ id: string }>("/api/v1/invoices/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      const id = uploadRes.data.id;
      setInvoiceId(id);
      setUploadStatus("PROCESSING");
      await apiClient.post(`/api/v1/invoices/extract/${id}`);
    } catch (err: any) {
      setUploadStatus("ERROR");
      setErrorMsg(err.response?.data?.detail || "Error al subir la factura");
    }
  };

  const getStepStatus = (stepName: string) => {
    if (uploadStatus === "ERROR") return "pending";
    if (!auditData) return uploadStatus === "PROCESSING" ? "loading" : "pending";

    const status = auditData.status;

    switch (stepName) {
      case "OCR":
        return status === InvoiceStatus.VALIDATED || status === InvoiceStatus.SIGNED || status === InvoiceStatus.SENT_OK
          ? "done"
          : "loading";
      case "VALIDATION":
        return status === InvoiceStatus.VALIDATED || status === InvoiceStatus.SIGNED || status === InvoiceStatus.SENT_OK
          ? "done"
          : "pending";
      case "SIGNING":
        return status === InvoiceStatus.SIGNED || status === InvoiceStatus.SENT_OK
          ? "done"
          : status === InvoiceStatus.VALIDATED
            ? "loading"
            : "pending";
      case "AEAT":
        return status === InvoiceStatus.SENT_OK ? "done" : status === InvoiceStatus.SIGNED ? "loading" : "pending";
      default:
        return "pending";
    }
  };

  return (
    <AppShell
      right={
        <div className="flex items-center gap-2 sm:gap-3">
          <div className="hidden md:block [&_div]:border-white/10 [&_div]:bg-white/5 [&_span]:text-slate-400 [&_select]:text-slate-100">
            <OrgSwitcher
              value={tenantId}
              onChange={setTenantId}
              orgs={[
                { id: "default", name: "Default", plan: "standard" },
                { id: "enterprise-demo", name: "Enterprise demo", plan: "enterprise" },
              ]}
            />
          </div>
          <div className="hidden lg:block">
            <ChainIntegrityBadgeLive issuerTaxId="B12345674" />
          </div>
        </div>
      }
    >
      <main className="relative z-10 mx-auto max-w-6xl space-y-10 px-5 py-10 sm:px-8">
        <section className="vf-card overflow-hidden rounded-[2rem]">
          <div className="grid lg:grid-cols-[1.15fr_0.85fr]">
            <div className="p-8 sm:p-10">
              <p className="vf-kicker">VeriFactu · Gemini 3.5 · Google ADK</p>
              <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white sm:text-5xl sm:leading-[1.05]">
                Agents that audit invoices.
                <span className="block text-emerald-300">Never the hash.</span>
              </h1>
              <p className="mt-4 max-w-lg text-sm leading-relaxed text-slate-400">
                Fortified Enterprise Fleet for Spanish fiscal compliance. Consult is tighten-only.
                Deterministic gates decide SIGN, ESCALATE, or BLOCK.
              </p>
              <div className="mt-7 flex flex-wrap gap-3">
                <Link
                  href="/fleet"
                  className="inline-flex items-center gap-2 rounded-full bg-emerald-400 px-5 py-2.5 text-sm font-semibold text-[#06110c] shadow-[0_0_32px_rgba(52,211,153,0.35)] transition hover:bg-emerald-300"
                >
                  Open judge console
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <a
                  href="#drop"
                  className="inline-flex items-center gap-2 rounded-full border border-white/12 px-5 py-2.5 text-sm text-slate-200 hover:border-white/25"
                >
                  Upload a PDF
                </a>
              </div>
              <ul className="mt-8 grid gap-3 sm:grid-cols-3">
                {[
                  { icon: Lock, title: "SIGNED", copy: "Tools write the chain." },
                  { icon: Scale, title: "ESCALATED", copy: "Math or memory fails." },
                  { icon: ShieldOff, title: "BLOCKED", copy: "Injection never signs." },
                ].map((item) => (
                  <li key={item.title} className="rounded-2xl border border-white/8 bg-white/3 px-3 py-3">
                    <item.icon className="h-4 w-4 text-emerald-300" />
                    <p className="mt-2 text-xs font-semibold uppercase tracking-[0.14em] text-white">{item.title}</p>
                    <p className="mt-1 text-xs text-slate-500">{item.copy}</p>
                  </li>
                ))}
              </ul>
            </div>
            <div className="relative min-h-[240px] border-t border-white/6 lg:border-l lg:border-t-0">
              <img
                src="/brand/hero-fortress.jpg"
                alt=""
                className="absolute inset-0 h-full w-full object-cover opacity-80"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-[#07090f] via-transparent to-transparent lg:bg-gradient-to-l" />
            </div>
          </div>
        </section>

        <section id="drop" className="vf-card rounded-[2rem] p-6 sm:p-8">
          <div className="mb-5 flex items-end justify-between gap-3">
            <div>
              <p className="vf-kicker">Smart Audit</p>
              <h2 className="mt-1 text-xl font-semibold text-white">Upload for the legacy extract path</h2>
            </div>
            <Link href="/history" className="text-xs text-slate-500 hover:text-emerald-300">
              Ledger →
            </Link>
          </div>
          <label className="group relative flex cursor-pointer flex-col items-center justify-center gap-4 rounded-3xl border border-dashed border-emerald-400/25 bg-emerald-400/5 px-6 py-14 transition hover:border-emerald-400/50 hover:bg-emerald-400/8">
            <input type="file" className="hidden" onChange={onFileChange} accept=".pdf,.xml" />
            <div className="rounded-full bg-emerald-400/10 p-4 text-emerald-300 transition group-hover:scale-105">
              <FileUp className="h-8 w-8" />
            </div>
            <div className="text-center">
              <h3 className="text-base font-semibold text-white">
                {file ? file.name : "Drop a PDF or XML invoice"}
              </h3>
              <p className="mt-1 text-sm text-slate-500">The contest demo lives on /fleet. This path still extracts.</p>
            </div>
            {uploadStatus === "UPLOADING" && (
              <div className="absolute inset-0 flex items-center justify-center rounded-3xl bg-[#07090f]/70">
                <Loader2 className="h-10 w-10 animate-spin text-emerald-400" />
              </div>
            )}
          </label>
          {errorMsg && (
            <p className="mt-4 rounded-xl border border-rose-400/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
              {errorMsg}
            </p>
          )}
        </section>

        <div className="grid gap-6 lg:grid-cols-2">
          <div className="vf-card rounded-[2rem] p-8">
            <h4 className="vf-kicker mb-6">Process</h4>
            <div className="relative space-y-7">
              <div className="absolute left-3 top-2 bottom-2 w-px bg-white/8" />
              <Step label="Leyendo PDF con IA" sub="OCR y extracción de campos clave" status={getStepStatus("OCR")} />
              <Step label="Validando importes" sub="Cálculo de Base + IVA = Total" status={getStepStatus("VALIDATION")} />
              <Step label="Generando Huella VeriFactu" sub="Firma digital y encadenamiento" status={getStepStatus("SIGNING")} />
              <Step label="Enviando a Hacienda" status={getStepStatus("AEAT")} />
            </div>
          </div>

          <div className="space-y-6">
            <div
              className={cn(
                "vf-card rounded-[2rem] p-8 transition",
                auditData?.status === InvoiceStatus.SENT_OK && "ring-1 ring-emerald-400/25",
                auditData?.status === InvoiceStatus.REJECTED_AEAT && "ring-1 ring-rose-400/25",
                auditData?.status === InvoiceStatus.SIGNED && "ring-1 ring-amber-400/25"
              )}
            >
              {auditData?.status === InvoiceStatus.REJECTED_AEAT ? (
                <ResultHead
                  icon={<XCircle className="h-7 w-7" />}
                  tone="rose"
                  title="Factura rechazada por AEAT"
                  body={auditData.message}
                  badge={<StatusBadge status={InvoiceStatus.REJECTED_AEAT} size="md" />}
                />
              ) : auditData?.status === InvoiceStatus.SENT_OK ? (
                <div className="space-y-6">
                  <ResultHead
                    icon={<CheckCircle2 className="h-7 w-7" />}
                    tone="emerald"
                    title="Factura enviada a Hacienda"
                    body="El registro ha sido completado."
                    badge={<StatusBadge status={InvoiceStatus.SENT_OK} size="md" />}
                  />
                  {auditData.aeat_csv && <CSVDisplay csv={auditData.aeat_csv} />}
                </div>
              ) : auditData?.status === InvoiceStatus.SIGNED ? (
                <ResultHead
                  icon={<AlertTriangle className="h-7 w-7" />}
                  tone="amber"
                  title="Pendiente de envío a AEAT"
                  body="Factura firmada, esperando conexión con Hacienda."
                  badge={<StatusBadge status={InvoiceStatus.SIGNED} size="md" />}
                />
              ) : (
                <ResultHead
                  icon={<Loader2 className="h-7 w-7 animate-spin" />}
                  tone="slate"
                  title="Auditoría en curso"
                  body={
                    auditData
                      ? `Procesando factura ${auditData.series}-${auditData.number}`
                      : "Selecciona un archivo o abre /fleet para la demo de jueces."
                  }
                />
              )}
            </div>
          </div>
        </div>
      </main>
    </AppShell>
  );
}

function ResultHead({
  icon,
  tone,
  title,
  body,
  badge,
}: {
  icon: React.ReactNode;
  tone: "emerald" | "rose" | "amber" | "slate";
  title: string;
  body?: string;
  badge?: React.ReactNode;
}) {
  const wrap = {
    emerald: "bg-emerald-400/15 text-emerald-300",
    rose: "bg-rose-400/15 text-rose-300",
    amber: "bg-amber-400/15 text-amber-200",
    slate: "bg-white/8 text-slate-300",
  }[tone];
  return (
    <div className="flex gap-4">
      <div className={cn("rounded-2xl p-3", wrap)}>{icon}</div>
      <div className="space-y-2">
        <h3 className="text-lg font-semibold text-white">{title}</h3>
        {body && <p className="text-sm leading-relaxed text-slate-400">{body}</p>}
        {badge}
      </div>
    </div>
  );
}

const Step = ({
  label,
  sub,
  status,
}: {
  label: string;
  sub?: string;
  status: "done" | "loading" | "pending";
}) => {
  return (
    <div className="relative z-10 flex gap-4">
      <div
        className={cn(
          "flex h-7 w-7 items-center justify-center rounded-full border-2",
          status === "done" && "border-emerald-400 bg-emerald-400 text-[#06110c]",
          status === "loading" && "border-sky-400 bg-[#0b1018] text-sky-300 ring-4 ring-sky-400/15",
          status === "pending" && "border-white/10 bg-[#0b1018] text-transparent"
        )}
      >
        {status === "done" ? <CheckCircle2 className="h-4 w-4" /> : status === "loading" ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
      </div>
      <div className="space-y-1 pt-0.5">
        <h5
          className={cn(
            "text-xs font-semibold uppercase tracking-wide",
            status === "pending" ? "text-slate-600" : "text-slate-100"
          )}
        >
          {label}
        </h5>
        {sub && <p className="text-[11px] text-slate-500">{sub}</p>}
      </div>
    </div>
  );
};
