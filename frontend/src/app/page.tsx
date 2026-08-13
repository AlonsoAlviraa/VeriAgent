"use client";

import { useEffect, useState, type ReactNode } from "react";
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
import { cn } from "@/lib/utils";
import { useLocale } from "@/components/i18n/locale-provider";
import { AgentRoster, type RosterAgent } from "@/components/fleet/agent-roster";
import type { MessageKey } from "@/lib/i18n";

const PROOFS: { title: MessageKey; body: MessageKey }[] = [
  { title: "landing.proof1.title", body: "landing.proof1.body" },
  { title: "landing.proof2.title", body: "landing.proof2.body" },
  { title: "landing.proof3.title", body: "landing.proof3.body" },
];

export default function HomePage() {
  const { t } = useLocale();
  const [file, setFile] = useState<File | null>(null);
  const [invoiceId, setInvoiceId] = useState<string | null>(null);
  const [tenantId, setTenantId] = useState<string>("default");
  const [uploadStatus, setUploadStatus] = useState<"IDLE" | "UPLOADING" | "PROCESSING" | "SUCCESS" | "ERROR">("IDLE");
  const [errorMsg, setErrorMsg] = useState("");
  const [dragging, setDragging] = useState(false);
  const [agents, setAgents] = useState<RosterAgent[] | null>(null);

  const { data: auditData } = useInvoiceStatus(invoiceId);

  useEffect(() => {
    apiClient
      .get<{ agents: RosterAgent[] }>("/api/v1/fleet/registry", {
        headers: { "X-Tenant-Id": "enterprise-demo", "X-User-Id": "judge", "X-Roles": "issuer" },
      })
      .then((res) => setAgents(res.data.agents || []))
      .catch(() => setAgents(null));
  }, []);

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
    } catch (err: unknown) {
      setUploadStatus("ERROR");
      const detail =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      setErrorMsg(detail || t("error.uploadFailed"));
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
        return "pending";
      default:
        return "pending";
    }
  };

  return (
    <AppShell>
      <section className="border-b border-[#e8e6e3]">
        <div className="mx-auto flex w-full max-w-[1120px] flex-col gap-8 px-4 py-12 md:px-6 md:py-20">
          <div className="max-w-[680px]">
            <p className="vf-label">{t("landing.kicker")}</p>
            <h1 className="vf-prose-hero mt-3">{t("landing.title")}</h1>
            <p className="mt-4 max-w-[520px] text-[16px] leading-relaxed text-[#6f6e69]">
              {t("landing.description")}
            </p>
            <div className="mt-7 flex flex-col gap-3 sm:flex-row sm:items-center">
              <Button
                render={<Link href="/fleet" />}
                nativeButton={false}
                variant="outline"
                className="h-10 w-full rounded-lg border-[#111] bg-[#111] px-4 text-[13px] font-medium text-white hover:bg-[#222] hover:text-white sm:w-auto"
              >
                {t("landing.cta")}
                <ArrowRight data-icon="inline-end" />
              </Button>
              <Button
                render={<Link href="/pricing" />}
                nativeButton={false}
                variant="outline"
                className="h-10 w-full rounded-lg border-[#e8e6e3] bg-white px-4 text-[13px] font-medium text-[#111] hover:bg-[#fafaf8] sm:w-auto"
              >
                {t("cta.pricing")}
              </Button>
            </div>
          </div>
          <p className="text-[12px] tracking-[0.02em] text-[#6f6e69]">{t("landing.builtWith")}</p>
        </div>
      </section>

      <AgentRoster agents={agents} />

      <section className="border-b border-[#e8e6e3]">
        <div className="mx-auto flex w-full max-w-[1120px] flex-col gap-4 px-4 py-8 md:px-6">
          <Button
            render={<Link href="/fleet" />}
            nativeButton={false}
            variant="outline"
            className="h-10 w-full rounded-lg border-[#111] bg-[#111] px-4 text-[13px] font-medium text-white hover:bg-[#222] hover:text-white sm:w-auto"
          >
            {t("landing.cta")}
            <ArrowRight data-icon="inline-end" />
          </Button>
          <p className="text-[13px] text-[#6f6e69]">
            <span className="font-medium text-[#111]">{t("demo.kicker")}</span>
            {" — "}
            {t("demo.pending")}
          </p>
        </div>
      </section>

      <section className="border-b border-[#e8e6e3]">
        <div className="mx-auto w-full max-w-[1120px] px-4 py-10 md:px-6 md:py-14">
          <p className="vf-label">{t("landing.proofKicker")}</p>
          <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-3">
            {PROOFS.map((proof) => (
              <article key={proof.title} className="vf-card rounded-lg p-5">
                <h2 className="text-[15px] font-medium tracking-tight text-[#111]">{t(proof.title)}</h2>
                <p className="mt-2 text-sm leading-relaxed text-[#6f6e69]">{t(proof.body)}</p>
              </article>
            ))}
          </div>
          <p className="mt-6 max-w-[640px] text-sm leading-relaxed text-[#6f6e69]">
            {t("landing.aeatLine")}{" "}
            <Link href="/tutorial" className="text-[#111] underline underline-offset-2">
              {t("landing.aeatLink")}
            </Link>
            .
          </p>
        </div>
      </section>

      <main className="mx-auto flex w-full max-w-[1120px] flex-col gap-6 px-4 py-10 md:px-6 md:py-14">
        <section id="drop" className="vf-card scroll-mt-24 rounded-lg p-4 sm:p-5">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="vf-label">{t("landing.extract")}</p>
              <h2 className="mt-1 text-[15px] font-medium tracking-tight text-[#111]">
                {t("landing.extractTitle")}
              </h2>
            </div>
            <label className="flex min-w-0 flex-col gap-1.5" data-testid="org-switcher">
              <span className="vf-label">{t("landing.tenant")}</span>
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
                {file ? file.name : t("landing.drop")}
              </span>
              <span className="mt-1 block text-[12px] text-[#6f6e69]">{t("landing.dropHint")}</span>
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
            <p className="vf-label">{t("landing.process")}</p>
            <div className="relative mt-5 flex flex-col gap-5">
              <div className="absolute top-2 bottom-2 left-3 w-px bg-[#e8e6e3]" />
              <Step label={t("landing.stepOcr")} sub={t("landing.stepOcrSub")} status={getStepStatus("OCR")} />
              <Step label={t("landing.stepValid")} sub={t("landing.stepValidSub")} status={getStepStatus("VALIDATION")} />
              <Step label={t("landing.stepHash")} sub={t("landing.stepHashSub")} status={getStepStatus("SIGNING")} />
              <Step label={t("landing.stepAeat")} sub={t("landing.stepAeatSub")} status="pending" />
            </div>
            <p className="mt-4 text-[12px] leading-relaxed text-[#6f6e69]">{t("landing.aeatQuiet")}</p>
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
                title={t("landing.rejected")}
                body={auditData.message}
                badge={<StatusBadge status={InvoiceStatus.REJECTED_AEAT} size="md" />}
              />
            ) : auditData?.status === InvoiceStatus.SENT_OK ? (
              <div className="flex flex-col gap-5">
                <ResultHead
                  icon={<CheckCircle2 className="size-5" />}
                  tone="emerald"
                  title={t("landing.sent")}
                  body={t("landing.sentBody")}
                  badge={<StatusBadge status={InvoiceStatus.SENT_OK} size="md" />}
                />
                {auditData.aeat_csv && <CSVDisplay csv={auditData.aeat_csv} />}
              </div>
            ) : auditData?.status === InvoiceStatus.SIGNED ? (
              <ResultHead
                icon={<AlertTriangle className="size-5" />}
                tone="amber"
                title={t("landing.pendingAeat")}
                body={t("landing.pendingAeatBody")}
                badge={<StatusBadge status={InvoiceStatus.SIGNED} size="md" />}
              />
            ) : (
              <ResultHead
                icon={<Loader2 className={cn("size-5", uploadStatus === "PROCESSING" && "animate-spin")} />}
                tone="slate"
                title={uploadStatus === "IDLE" ? t("landing.awaiting") : t("landing.inProgress")}
                body={
                  auditData
                    ? t("landing.processingInvoice", { series: auditData.series, number: auditData.number })
                    : t("landing.selectFile")
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
  icon: ReactNode;
  tone: "emerald" | "rose" | "amber" | "slate";
  title: string;
  body?: string;
  badge?: ReactNode;
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
        {status === "done" ? (
          <CheckCircle2 className="size-4" />
        ) : status === "loading" ? (
          <Loader2 className="size-4 animate-spin" />
        ) : null}
      </div>
      <div className="flex flex-col gap-0.5 pt-0.5">
        <h5 className={cn("text-[13px] font-medium", status === "pending" ? "text-[#cfcbc4]" : "text-[#111]")}>
          {label}
        </h5>
        {sub && <p className="text-[12px] text-[#6f6e69]">{sub}</p>}
      </div>
    </div>
  );
};
