import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { asVerdict } from "./verdict";
import { PipelineStepper } from "./pipeline-stepper";
import type { FleetRunView } from "./recent-runs";
import { shortHash, VerdictPill } from "./verdict-pill";

export function ResultCard({
  run,
  background202,
}: {
  run: FleetRunView | null;
  background202: boolean;
}) {
  const pending = Boolean(run && (run.status === "QUEUED" || run.status === "RUNNING"));
  const accepted202 = Boolean(run && (background202 || run.status === "QUEUED"));

  return (
    <section
      aria-label="Latest result"
      className={cn("vf-card rounded-lg p-4 sm:p-5", run && "vf-enter")}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="vf-label">Result</p>
          <h2 className="mt-1 text-[15px] font-medium tracking-tight text-[#111]">
            {run ? "Last dispatch" : "Dispatch a fixture to see a verdict"}
          </h2>
        </div>
        {run ? (
          pending ? (
            <span className="inline-flex items-center gap-1.5 rounded-md border border-[#e8e6e3] bg-[#f4f3f0] px-2 py-0.5 text-[12px] text-[#6f6e69]">
              <Loader2 className="size-3 animate-spin" aria-hidden />
              {accepted202 ? "202 accepted · settling" : "Running"}
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
            {run.invoice_hash ? shortHash(run.invoice_hash) : pending ? "hash pending · tools only" : "no hash written"}
          </p>
          {accepted202 && (
            <p className="mt-2 text-[12px] text-[#6f6e69]">
              {pending
                ? "Background 202 · accepted, waiting to settle"
                : "Background 202 · settled"}
            </p>
          )}
          <div className="mt-5">
            <PipelineStepper run={run} />
          </div>
        </>
      ) : (
        <p className="mt-3 text-[14px] leading-relaxed text-[#6f6e69]">
          Ingest, consult (tighten only), then tools write the hash. The model never writes it.
        </p>
      )}
    </section>
  );
}
