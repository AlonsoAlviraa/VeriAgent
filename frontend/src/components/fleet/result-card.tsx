"use client";

import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { asVerdict } from "./verdict";
import { PipelineStepper } from "./pipeline-stepper";
import type { FleetRunView } from "./recent-runs";
import { shortHash, VerdictPill } from "./verdict-pill";
import { useLocale } from "@/components/i18n/locale-provider";

export function ResultCard({
  run,
  background202,
}: {
  run: FleetRunView | null;
  background202: boolean;
}) {
  const { t } = useLocale();
  const pending = Boolean(run && (run.status === "QUEUED" || run.status === "RUNNING"));
  const accepted202 = Boolean(run && (background202 || run.status === "QUEUED"));

  return (
    <section
      aria-label={t("result.aria")}
      className={cn("vf-card rounded-lg p-4 sm:p-5", run && "vf-enter")}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="vf-label">{t("result.label")}</p>
          <h2 className="mt-1 text-[15px] font-medium tracking-tight text-[#111]">
            {run ? t("result.lastDispatch") : t("result.emptyTitle")}
          </h2>
        </div>
        {run ? (
          pending ? (
            <span className="inline-flex items-center gap-1.5 rounded-md border border-[#e8e6e3] bg-[#f4f3f0] px-2 py-0.5 text-[12px] text-[#6f6e69]">
              <Loader2 className="size-3 animate-spin" aria-hidden />
              {accepted202 ? t("result.acceptedSettling") : t("result.running")}
            </span>
          ) : (
            <VerdictPill verdict={asVerdict(run.decision)} />
          )
        ) : null}
      </div>

      {run ? (
        <>
          <p className="mt-3 text-[14px] leading-relaxed text-[#111]">{run.reason}</p>
          <p className="mt-2 font-mono text-[13px] text-[#6f6e69]">
            {run.invoice_hash ? shortHash(run.invoice_hash) : pending ? t("result.hashPending") : t("result.noHash")}
          </p>
          {accepted202 && (
            <p className="mt-2 text-[12px] text-[#6f6e69]">
              {pending ? t("result.bgPending") : t("result.bgSettled")}
            </p>
          )}
        </>
      ) : (
        <p className="mt-3 text-[14px] leading-relaxed text-[#6f6e69]">
          {t("result.emptyBody")}
        </p>
      )}
      <div className="mt-5">
        <PipelineStepper run={run} />
      </div>
    </section>
  );
}
