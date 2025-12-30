"use client";

import React, { useState } from "react";
import {
  FileUp,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Loader2,
  ShieldCheck,
  Download,
  MoreVertical,
  ExternalLink,
  Info,
  User
} from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// ==========================================
// DATA MOCKS
// ==========================================
const RECENT_HISTORY = [
  { id: 1, date: "14 Oct 2023, 10:42", issuer: "Amazon Web Services", logo: "AWS", amount: "45,20 €", status: "SENT_OK", csv: "ES-29384-XJ9" },
  { id: 2, date: "12 Oct 2023, 16:15", issuer: "Restaurante El Paso", logo: "EP", amount: "120,50 €", status: "SIGNED" },
  { id: 3, date: "10 Oct 2023, 09:30", issuer: "PC Componentes", logo: "PC", amount: "899,00 €", status: "REJECTED_AEAT" },
];

// Import new components
import { StatusBadge } from "@/components/ui/status-badge";
import { CSVDisplay } from "@/components/ui/csv-display";

import { useInvoiceStatus } from "@/hooks/use-invoice";
import apiClient from "@/lib/api-client";
import { InvoiceStatus } from "@/lib/types/api";

export default function SmartAuditDashboard() {
  const [file, setFile] = useState<File | null>(null);
  const [invoiceId, setInvoiceId] = useState<string | null>(null);
  const [uploadStatus, setUploadStatus] = useState<"IDLE" | "UPLOADING" | "PROCESSING" | "SUCCESS" | "ERROR">("IDLE");
  const [errorMsg, setErrorMsg] = useState("");

  const { data: auditData, isLoading: isPolling } = useInvoiceStatus(invoiceId);

  const onFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;

    setFile(selectedFile);
    setUploadStatus("UPLOADING");
    setErrorMsg("");

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      // 1. Upload
      const uploadRes = await apiClient.post<{ id: string }>("/api/v1/invoices/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });

      const id = uploadRes.data.id;
      setInvoiceId(id);
      setUploadStatus("PROCESSING");

      // 2. Trigger Extraction (Backend should handle extraction + crew audit automatically in a real flow)
      // Here we assume the backend starts the process upon upload or we call extract:
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
        return (status === InvoiceStatus.VALIDATED || status === InvoiceStatus.SIGNED || status === InvoiceStatus.SENT_OK) ? "done" : "loading";
      case "VALIDATION":
        return (status === InvoiceStatus.VALIDATED || status === InvoiceStatus.SIGNED || status === InvoiceStatus.SENT_OK) ? "done" : "pending";
      case "SIGNING":
        return (status === InvoiceStatus.SIGNED || status === InvoiceStatus.SENT_OK) ? "done" : (status === InvoiceStatus.VALIDATED ? "loading" : "pending");
      case "AEAT":
        return (status === InvoiceStatus.SENT_OK) ? "done" : (status === InvoiceStatus.SIGNED ? "loading" : "pending");
      default: return "pending";
    }
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC]">
      {/* Top Navigation */}
      <nav className="flex items-center justify-between px-8 py-4 bg-white border-b border-slate-100">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-emerald-500 rounded-lg text-white">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <span className="font-bold text-slate-800 text-lg">VeriAgent</span>
        </div>
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-50 text-emerald-600 text-[11px] font-bold border border-emerald-100 uppercase tracking-tight">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Conectado con AEAT
          </div>
          <div className="w-10 h-10 rounded-full bg-slate-200 overflow-hidden ring-2 ring-slate-100 cursor-pointer">
            <User className="w-full h-full p-2 text-slate-400" />
          </div>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto px-8 py-10 space-y-12">
        {/* Hero Section */}
        <div className="text-center space-y-3">
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">Auditoría de Facturas Inteligente</h1>
          <p className="text-slate-500">Sube tus documentos para validación automática y envío a Hacienda</p>
        </div>

        {/* Dropzone Area */}
        <section className="bg-white rounded-[2rem] p-8 shadow-sm border border-slate-100">
          <label className="border-2 border-dashed border-emerald-200 rounded-3xl p-16 flex flex-col items-center justify-center gap-4 bg-emerald-50/10 hover:bg-emerald-50/30 transition-all cursor-pointer group relative">
            <input type="file" className="hidden" onChange={onFileChange} accept=".pdf,.xml" />
            <div className="p-4 bg-emerald-500/10 rounded-full text-emerald-600 group-hover:scale-110 transition-transform">
              <FileUp className="w-10 h-10" />
            </div>
            <div className="text-center">
              <h3 className="font-bold text-slate-800 text-lg">
                {file ? file.name : "Arrastra tu factura aquí para auditarla"}
              </h3>
              <p className="text-slate-400 text-sm">Soporta PDF y XML para validación automática</p>
            </div>
            {uploadStatus === "UPLOADING" && (
              <div className="absolute inset-0 bg-white/80 flex items-center justify-center rounded-3xl">
                <Loader2 className="w-12 h-12 text-emerald-500 animate-spin" />
              </div>
            )}
          </label>
        </section>

        {/* Status and Result Grid */}
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Left: Process steps */}
          <div className="bg-white rounded-[2rem] p-8 shadow-sm border border-slate-100 space-y-6">
            <h4 className="text-[11px] font-black text-slate-400 uppercase tracking-[0.2em] mb-8">Estado del Proceso</h4>
            <div className="space-y-8 relative">
              {/* Path line */}
              <div className="absolute left-3 top-2 bottom-2 w-px bg-slate-100 z-0" />

              <Step label="Leyendo PDF con IA" sub="OCR y extracción de campos clave" status={getStepStatus("OCR")} />
              <Step label="Validando importes" sub="Cálculo de Base + IVA = Total" status={getStepStatus("VALIDATION")} />
              <Step label="Generando Huella VeriFactu" sub="Firma digital y encadenamiento" status={getStepStatus("SIGNING")} />
              <Step label="Enviando a Hacienda" status={getStepStatus("AEAT")} last />
            </div>
          </div>

          {/* Right: Result card */}
          <div className="space-y-6">
            <div className={cn(
              "rounded-[2rem] p-8 transition-all duration-700",
              auditData?.status === InvoiceStatus.SENT_OK
                ? "bg-emerald-50/80 border-2 border-emerald-500/10 shadow-xl shadow-emerald-500/5 translate-y-0 opacity-100"
                : auditData?.status === InvoiceStatus.REJECTED_AEAT
                  ? "bg-red-50/80 border-2 border-red-500/10 shadow-xl translate-y-0 opacity-100"
                  : auditData?.status === InvoiceStatus.SIGNED
                    ? "bg-amber-50/80 border-2 border-amber-500/10 shadow-xl translate-y-0 opacity-100"
                    : "bg-slate-50 opacity-50 translate-y-4"
            )}>
              {auditData?.status === InvoiceStatus.REJECTED_AEAT ? (
                <div className="flex gap-4">
                  <div className="p-3 bg-red-500 rounded-2xl text-white">
                    <XCircle className="w-8 h-8" />
                  </div>
                  <div className="space-y-1">
                    <h3 className="text-xl font-black text-red-900">Factura Rechazada por AEAT</h3>
                    <p className="text-sm text-red-700 leading-relaxed italic">{auditData.message}</p>
                    <StatusBadge status={InvoiceStatus.REJECTED_AEAT} size="md" />
                  </div>
                </div>
              ) : auditData?.status === InvoiceStatus.SENT_OK ? (
                <div className="space-y-6">
                  <div className="flex gap-4">
                    <div className="p-3 bg-emerald-500 rounded-2xl text-white">
                      <CheckCircle2 className="w-8 h-8" />
                    </div>
                    <div className="space-y-1">
                      <h3 className="text-xl font-black text-emerald-900">Factura Enviada a Hacienda</h3>
                      <p className="text-sm text-emerald-700 leading-relaxed italic">
                        El registro ha sido completado exitosamente.
                      </p>
                      <StatusBadge status={InvoiceStatus.SENT_OK} size="md" />
                    </div>
                  </div>
                  {auditData.aeat_csv && (
                    <CSVDisplay csv={auditData.aeat_csv} />
                  )}
                </div>
              ) : auditData?.status === InvoiceStatus.SIGNED ? (
                <div className="flex gap-4">
                  <div className="p-3 bg-amber-500 rounded-2xl text-white">
                    <AlertTriangle className="w-8 h-8" />
                  </div>
                  <div className="space-y-1">
                    <h3 className="text-xl font-black text-amber-900">Pendiente de Envio a AEAT</h3>
                    <p className="text-sm text-amber-700 leading-relaxed italic">
                      Factura firmada, esperando conexion con Hacienda.
                    </p>
                    <StatusBadge status={InvoiceStatus.SIGNED} size="md" />
                  </div>
                </div>
              ) : (
                <div className="flex gap-4">
                  <div className="p-3 bg-slate-300 rounded-2xl text-white">
                    <Loader2 className="w-8 h-8 animate-spin" />
                  </div>
                  <div className="space-y-1">
                    <h3 className="text-xl font-black text-slate-700">Auditoria en Curso</h3>
                    <p className="text-sm text-slate-500 leading-relaxed italic">
                      {auditData ? `Procesando factura ${auditData.series}-${auditData.number}` : "Selecciona un archivo para comenzar."}
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Hint box */}
            <div className="bg-blue-50/80 border border-blue-100 rounded-2xl p-6 flex gap-4 items-center">
              <div className="p-2 bg-blue-500 rounded-full text-white">
                <Info className="w-4 h-4" />
              </div>
              <p className="text-xs text-blue-700 font-medium leading-relaxed">
                Recuerda que tienes hasta el día 20 para presentar tus liquidaciones trimestrales.
              </p>
            </div>
          </div>
        </div>

        {/* History Table */}
        <section className="bg-white rounded-[2rem] p-8 shadow-sm border border-slate-100 overflow-hidden">
          <div className="flex items-center justify-between mb-8">
            <h3 className="text-lg font-black text-slate-800">Historial Reciente</h3>
            <button className="text-emerald-500 text-sm font-bold hover:underline">Ver todo →</button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="text-[11px] font-black text-slate-400 uppercase tracking-widest border-b border-slate-50">
                  <th className="pb-4 font-black">Fecha</th>
                  <th className="pb-4 font-black">Emisor</th>
                  <th className="pb-4 font-black text-right">Importe Total</th>
                  <th className="pb-4 font-black pl-8">Estado</th>
                  <th className="pb-4"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {RECENT_HISTORY.map((item) => (
                  <tr key={item.id} className="group hover:bg-slate-50/50 transition-colors">
                    <td className="py-5 text-sm text-slate-500">{item.date}</td>
                    <td className="py-5">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-slate-900 flex items-center justify-center text-[10px] font-black text-white">
                          {item.logo}
                        </div>
                        <span className="font-bold text-slate-700 text-sm">{item.issuer}</span>
                      </div>
                    </td>
                    <td className="py-5 text-sm font-black text-slate-800 text-right font-mono">{item.amount}</td>
                    <td className="py-5 pl-8">
                      <StatusBadge status={item.status} />
                    </td>
                    <td className="py-5 text-right pr-2">
                      <button className="p-2 hover:bg-slate-100 rounded-lg text-slate-300">
                        <MoreVertical className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}

const Step = ({ label, sub, status, last }: { label: string; sub?: string; status: "done" | "loading" | "pending"; last?: boolean }) => {
  return (
    <div className="flex gap-4 group relative z-10">
      <div className={cn(
        "w-7 h-7 rounded-full flex items-center justify-center border-2 transition-all duration-500",
        status === "done" ? "bg-emerald-500 border-emerald-500 text-white" :
          status === "loading" ? "bg-white border-blue-500 text-blue-500 animate-pulse ring-4 ring-blue-100" :
            "bg-white border-slate-100 text-slate-100"
      )}>
        {status === "done" ? <CheckCircle2 className="w-4 h-4" /> :
          status === "loading" ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
      </div>
      <div className="space-y-1 pt-0.5">
        <h5 className={cn("text-xs font-black uppercase tracking-tight transition-colors", status === "pending" ? "text-slate-200" : "text-slate-800")}>
          {label}
        </h5>
        {sub && <p className="text-[10px] text-slate-400 font-medium italic">{sub}</p>}
      </div>
    </div>
  );
};
