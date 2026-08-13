"use client";

import { cn } from "@/lib/utils";
import type { FleetRunView } from "./recent-runs";
import { shortHash } from "./verdict-pill";
import { useLocale } from "@/components/i18n/locale-provider";

type StepState = "pending" | "current" | "done" | "skipped";

function stepState(run: FleetRunView | null): {
  ingest: StepState;
  consult: StepState;
  hash: StepState;
} {
  if (!run) return { ingest: "pending", consult: "pending", hash: "pending" };
  const pending = run.status === "QUEUED" || run.status === "RUNNING";
  if (pending) {
    return { ingest: "done", consult: "current", hash: "pending" };
  }
  return {
    ingest: "done",
    consult: "done",
    hash: run.invoice_hash ? "done" : "skipped",
  };
}

export function PipelineStepper({ run }: { run: FleetRunView | null }) {
  const { t } = useLocale();
  const s = stepState(run);
  const consultNote = run?.adk?.consult?.invoked
    ? t("step.consultInvoked", { rec: run.adk.consult.recommendation || "invoked" })
    : run && s.consult === "done"
      ? t("step.consultNotInvoked")
      : t("step.consultNever");

  return (
    <ol className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <Step n={1} label={t("step.ingest")} detail={t("step.ingestDetail")} state={s.ingest} />
      <Step n={2} label={t("step.consult")} detail={consultNote} state={s.consult} tighten={t("step.tightenOnly")} />
      <Step
        n={3}
        label={t("step.hash")}
        detail={
          run?.invoice_hash
            ? shortHash(run.invoice_hash)
            : s.hash === "skipped"
              ? t("step.hashSkipped")
              : t("step.hashTools")
        }
        state={s.hash}
      />
    </ol>
  );
}

function Step({
  n,
  label,
  detail,
  state,
  tighten,
}: {
  n: number;
  label: string;
  detail: string;
  state: StepState;
  tighten?: string;
}) {
  return (
    <li
      className={cn(
        "rounded-lg border px-3 py-3",
        state === "done" && "border-[#c8e6d3] bg-[#eef8f1]",
        state === "current" && "border-[#e8e6e3] bg-white",
        state === "pending" && "border-[#e8e6e3] bg-[#fbfbf9]",
        state === "skipped" && "border-[#e8e6e3] bg-[#f4f3f0]"
      )}
    >
      <p className="vf-label">
        {n} · {label}
        {tighten ? ` · ${tighten}` : ""}
      </p>
      <p
        className={cn(
          "mt-1 text-[13px] leading-snug",
          state === "pending" ? "text-[#6f6e69]" : "text-[#111]"
        )}
      >
        {detail}
      </p>
    </li>
  );
}
