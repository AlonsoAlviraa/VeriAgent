import { Hash, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { VerdictPill } from "./verdict-pill";

export type FleetRunView = {
  run_id: string;
  status: string;
  decision: string;
  reason: string;
  invoice_hash?: string | null;
  armor?: { allowed?: boolean; classifier?: string };
  adk?: { consult?: { invoked?: boolean; recommendation?: string; model?: string; runner?: string } };
  pubsub?: { published?: boolean; topic?: string; reason?: string };
};

function shortHash(hash: string) {
  if (hash.length <= 20) return hash;
  return `${hash.slice(0, 8)}…${hash.slice(-8)}`;
}

export function RecentRuns({
  runs,
  live,
  runner,
}: {
  runs: FleetRunView[];
  live: FleetRunView | null;
  runner: string;
}) {
  const pending = live && (live.status === "QUEUED" || live.status === "RUNNING");
  const terminal = Boolean(live) && !pending;

  return (
    <section aria-label="Recent runs" className="vf-panel flex flex-col rounded-sm">
      <header className="flex items-center justify-between border-b border-[#1b2740] px-3 py-2.5">
        <h2 className="font-mono text-[10px] uppercase tracking-[0.22em] text-slate-500">
          Recent runs
        </h2>
        <span className="font-mono text-[10px] text-slate-600">
          {String(runs.length).padStart(2, "0")} in session
        </span>
      </header>

      {live && (
        <div className="border-b border-[#1b2740] px-3 py-3">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="font-mono text-[9px] uppercase tracking-[0.16em] text-slate-600">
                Last decision
              </p>
              <p className="mt-1 truncate font-mono text-[10px] text-slate-500">{live.run_id}</p>
            </div>
            {pending ? (
              <span
                className={cn(
                  "flex shrink-0 items-center gap-1.5 rounded-sm border bg-[#0b1220] px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.14em] text-slate-400",
                  live.status === "QUEUED"
                    ? "vf-status-queued border-amber-400/35 text-amber-200"
                    : "border-[#243350]"
                )}
              >
                <Loader2 className="size-3 animate-spin" aria-hidden />
                {live.status === "QUEUED" ? "202" : live.status}
              </span>
            ) : (
              <span className={cn(live.status === "COMPLETED" && "vf-status-completed")}>
                <VerdictPill
                  key={`${live.run_id}:${live.status}:${live.decision}`}
                  verdict={live.decision}
                  glow={live.decision === "SIGNED"}
                  pulse={terminal}
                />
              </span>
            )}
          </div>
          <p className="mt-2 text-[12px] leading-snug text-slate-400">{live.reason}</p>
          {live.invoice_hash ? (
            <p className="mt-2 flex flex-col gap-1 font-mono text-[10px] text-slate-500">
              <span className="flex items-center gap-1.5">
                <Hash className="size-3 text-emerald-400/70" aria-hidden />
                <span className="vf-hash-reveal text-emerald-300/80">{shortHash(live.invoice_hash)}</span>
              </span>
              <span className="break-all text-slate-600">{live.invoice_hash}</span>
            </p>
          ) : (
            <p className="mt-2 font-mono text-[10px] text-slate-600">
              {pending ? "accepted 202 · fleet working" : "no hash written"}
            </p>
          )}
          <div className="mt-3 grid grid-cols-3 gap-px overflow-hidden rounded-sm border border-[#1b2740] bg-[#1b2740]">
            <Meta title="Armor" value={live.armor?.allowed === false ? "BLOCKED" : "clean"} />
            <Meta
              title="ADK"
              value={live.adk?.consult?.invoked ? live.adk.consult.recommendation || "invoked" : "offline"}
              detail={live.adk?.consult?.runner || live.adk?.consult?.model || runner}
            />
            <Meta
              title="Pub/Sub"
              value={live.pubsub?.published ? "published" : "local no-op"}
              detail={live.pubsub?.topic || live.pubsub?.reason}
            />
          </div>
        </div>
      )}

      {runs.length === 0 && !live ? (
        <p className="px-3 py-6 text-center font-mono text-[11px] text-slate-600">
          No runs yet — dispatch a fixture.
        </p>
      ) : (
        <ol className="vf-scroll max-h-[280px] divide-y divide-[#161f33] overflow-y-auto">
          {runs.slice(0, 12).map((run, index) => {
            const queued = run.status === "QUEUED" || run.status === "RUNNING";
            return (
              <li key={run.run_id} className="flex items-start gap-3 px-3 py-2.5">
                <span className="mt-0.5 w-8 shrink-0 font-mono text-[10px] tabular-nums text-slate-600">
                  #{String(runs.length - index).padStart(3, "0")}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-[12px] font-medium tracking-tight text-slate-200">
                      {run.reason}
                    </span>
                    {queued ? (
                      <span className="flex shrink-0 items-center gap-1.5 rounded-sm border border-[#243350] bg-[#0b1220] px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.14em] text-slate-400">
                        <Loader2 className="size-3 animate-spin" aria-hidden />
                        {run.status === "QUEUED" ? "202" : run.status}
                      </span>
                    ) : (
                      <VerdictPill verdict={run.decision} />
                    )}
                  </div>
                  <p className="mt-1 flex items-center gap-1.5 font-mono text-[10px] text-slate-500">
                    {run.invoice_hash ? (
                      <>
                        <Hash className="size-3 text-emerald-400/70" aria-hidden />
                        <span className="text-emerald-300/80">{shortHash(run.invoice_hash)}</span>
                      </>
                    ) : (
                      <span className="text-slate-600">no hash written</span>
                    )}
                  </p>
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}

function Meta({ title, value, detail }: { title: string; value: string; detail?: string }) {
  return (
    <div className="bg-[#0b1220] px-2 py-2">
      <p className="font-mono text-[8px] uppercase tracking-[0.16em] text-slate-600">{title}</p>
      <p className="mt-0.5 truncate text-[11px] text-slate-200">{value}</p>
      {detail && <p className="truncate font-mono text-[9px] text-slate-600">{detail}</p>}
    </div>
  );
}
