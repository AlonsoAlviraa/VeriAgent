import { cn } from "@/lib/utils";
import type { FleetRunView } from "./recent-runs";
import { shortHash } from "./verdict-pill";

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
  const s = stepState(run);
  const consultNote = run?.adk?.consult?.invoked
    ? `tighten only · ${run.adk.consult.recommendation || "invoked"}`
    : run && s.consult === "done"
      ? "tighten only · not invoked"
      : "tighten only · never writes the hash";

  return (
    <ol className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <Step n={1} label="Ingest" detail="Fixture or PDF accepted" state={s.ingest} />
      <Step n={2} label="Consult" detail={consultNote} state={s.consult} tighten />
      <Step
        n={3}
        label="Hash"
        detail={
          run?.invoice_hash
            ? shortHash(run.invoice_hash)
            : s.hash === "skipped"
              ? "not written · tools only"
              : "tools write this"
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
  tighten = false,
}: {
  n: number;
  label: string;
  detail: string;
  state: StepState;
  tighten?: boolean;
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
        {tighten ? " · tighten only" : ""}
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
