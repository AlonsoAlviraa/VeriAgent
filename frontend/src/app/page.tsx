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
} from "lucide-react";
import { StatusBadge } from "@/components/ui/status-badge";
import { CSVDisplay } from "@/components/ui/csv-display";
import { useInvoiceStatus } from "@/hooks/use-invoice";
import apiClient, { TENANT_STORAGE_KEY } from "@/lib/api-client";
import { InvoiceStatus } from "@/lib/types/api";
import { AppShell } from "@/components/shell/app-shell";
import { Button } from "@/components/ui/button";
import { FleetHero } from "@/components/fleet/hero";
import { cn } from "@/lib/utils";

export default function AuditPage() {
  const [file, setFile] = useState<File | null>(null);
  const [invoiceId, setInvoiceId] = useState<string | null>(null);
  const [tenantId, setTenantId] = useState<string>("default");
  const [uploadStatus, setUploadStatus] = useState<"IDLE" | "UPLOADING" | "PROCESSING" | "SUCCESS" | "ERROR">("IDLE");
  const [errorMsg, setErrorMsg] = useState("");
  const [dragging, setDragging] = useState(false);

  const { data: auditData } = useInvoiceStatus(invoiceId);

  const setTenant = (id: string) => {
    setTenantId(id);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(TENANT_STORAGE_KEY, id);
    }
  };

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
      setErrorMsg(err.response?.data?.detail || "Upload failed");
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
    <AppShell>
      <FleetHero
        kicker="The LLM never writes the hash."
        title="Check an invoice before the fleet signs it."
        description="Upload a PDF or XML to extract fields. Then open the judge console and dispatch a fixture — you’ll see the verdict and hash, not a chat."
        actions={
          <Button
            render={<Link href="/fleet" />}
            nativeButton={false}
            size="lg"
            className="h-10 rounded-md bg-[#111] px-4 text-[13px] font-medium text-white transition-colors duration-150 hover:bg-[#18794e]"
          >
            Open judge console
            <ArrowRight data-icon="inline-end" />
          </Button>
        }
      />

      <main className="mx-auto flex w-full max-w-[1120px] flex-col gap-6 px-4 py-6 md:px-6 md:py-8">
        <section id="drop" className="vf-card rounded-lg p-4 sm:p-5">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="vf-label">Extract</p>
              <h2 className="mt-1 text-[15px] font-medium tracking-tight text-[#111]">
                Drop a PDF or XML invoice
              </h2>
            </div>
            <label className="flex min-w-0 flex-col gap-1.5" data-testid="org-switcher">
              <span className="vf-label">Tenant</span>
              <select
                data-testid="org-switcher-select"
                className="h-10 rounded-md border border-[#e8e6e3] bg-white px-3 text-[13px] text-[#111] outline-none sm:h-8"
                value={tenantId}
                onChange={(e) => setTenant(e.target.value)}
              >
                <option value="default">default</option>
                <option value="enterprise-demo">enterprise-demo</option>
              </select>
            </label>
          </div>
          <label
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={() => setDragging(false)}
            className={cn(
              "group relative flex min-h-[148px] cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border border-dashed px-4 py-10 transition-colors duration-150",
              dragging ? "border-[#18794e] bg-[#eef8f1]" : "border-[#e8e6e3] bg-[#fafaf8] hover:border-[#cfcbc4]"
            )}
          >
            <input type="file" className="hidden" onChange={onFileChange} accept=".pdf,.xml" />
            <span className="flex size-10 items-center justify-center rounded-md border border-[#e8e6e3] bg-white text-[#18794e]">
              <FileUp className="size-5" />
            </span>
            <span className="text-center">
              <span className="block text-[14px] font-medium text-[#111]">
                {file ? file.name : "Drop a file or click to browse"}
              </span>
              <span className="mt-1 block text-[12px] text-[#6f6e69]">
                PDF or XML · contest fixtures live on /fleet
              </span>
            </span>
          </label>
          {errorMsg && (
            <p className="mt-4 rounded-lg border border-[#f0c7c3] bg-[#fbefee] px-4 py-3 text-sm text-[#9b2c2c]">
              {errorMsg}
            </p>
          )}
        </section>

        <div className="grid gap-4 lg:grid-cols-2">
          <section className="vf-card rounded-lg px-4 py-5">
            <p className="vf-label">Process</p>
            <div className="relative mt-5 flex flex-col gap-5">
              <div className="absolute top-2 bottom-2 left-3 w-px bg-[#e8e6e3]" />
              <Step label="Reading PDF" sub="OCR and key-field extraction" status={getStepStatus("OCR")} />
              <Step label="Validating amounts" sub="Base + VAT = Total" status={getStepStatus("VALIDATION")} />
              <Step label="Writing VeriFactu hash" sub="Digital signature and chaining" status={getStepStatus("SIGNING")} />
              <Step label="Submitting to AEAT" status={getStepStatus("AEAT")} />
            </div>
          </section>

          <section
            className={cn(
              "vf-card rounded-lg p-5",
              auditData?.status === InvoiceStatus.SENT_OK && "border-[#c8e6d3]",
              auditData?.status === InvoiceStatus.REJECTED_AEAT && "border-[#f0c7c3]",
              auditData?.status === InvoiceStatus.SIGNED && "border-[#f3d5b0]"
            )}
          >
            {auditData?.status === InvoiceStatus.REJECTED_AEAT ? (
              <ResultHead
                icon={<XCircle className="size-5" />}
                tone="rose"
                title="Rejected by AEAT"
                body={auditData.message}
                badge={<StatusBadge status={InvoiceStatus.REJECTED_AEAT} size="md" />}
              />
            ) : auditData?.status === InvoiceStatus.SENT_OK ? (
              <div className="flex flex-col gap-5">
                <ResultHead
                  icon={<CheckCircle2 className="size-5" />}
                  tone="emerald"
                  title="Sent to AEAT"
                  body="The registry record is complete."
                  badge={<StatusBadge status={InvoiceStatus.SENT_OK} size="md" />}
                />
                {auditData.aeat_csv && <CSVDisplay csv={auditData.aeat_csv} />}
              </div>
            ) : auditData?.status === InvoiceStatus.SIGNED ? (
              <ResultHead
                icon={<AlertTriangle className="size-5" />}
                tone="amber"
                title="Pending AEAT submission"
                body="Invoice signed, waiting on Hacienda connectivity."
                badge={<StatusBadge status={InvoiceStatus.SIGNED} size="md" />}
              />
            ) : (
              <ResultHead
                icon={<Loader2 className={cn("size-5", uploadStatus === "PROCESSING" && "animate-spin")} />}
                tone="slate"
                title={uploadStatus === "IDLE" ? "Awaiting file" : "Audit in progress"}
                body={
                  auditData
                    ? `Processing invoice ${auditData.series}-${auditData.number}`
                    : "Select a file, or open /fleet for the judge demo."
                }
              />
            )}
          </section>
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
    emerald: "bg-[#eef8f1] text-[#17663f]",
    rose: "bg-[#fbefee] text-[#9b2c2c]",
    amber: "bg-[#fbf3e8] text-[#9a4d09]",
    slate: "bg-[#f4f3f0] text-[#6f6e69]",
  }[tone];
  return (
    <div className="flex gap-4">
      <div className={cn("rounded-md p-2.5", wrap)}>{icon}</div>
      <div className="flex flex-col gap-2">
        <h3 className="text-[15px] font-medium tracking-tight text-[#111]">{title}</h3>
        {body && <p className="text-sm leading-relaxed text-[#6f6e69]">{body}</p>}
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
          "flex size-7 items-center justify-center rounded-md border",
          status === "done" && "border-[#c8e6d3] bg-[#18794e] text-white",
          status === "loading" && "border-[#c8e6d3] bg-white text-[#18794e]",
          status === "pending" && "border-[#e8e6e3] bg-white text-transparent"
        )}
      >
        {status === "done" ? <CheckCircle2 className="size-4" /> : status === "loading" ? <Loader2 className="size-4 animate-spin" /> : null}
      </div>
      <div className="flex flex-col gap-0.5 pt-0.5">
        <h5
          className={cn(
            "text-[13px] font-medium",
            status === "pending" ? "text-[#cfcbc4]" : "text-[#111]"
          )}
        >
          {label}
        </h5>
        {sub && <p className="text-[12px] text-[#6f6e69]">{sub}</p>}
      </div>
    </div>
  );
};
