import { Loader2 } from "lucide-react";
import { asVerdict } from "./verdict";
import { HashReveal } from "./hash-reveal";
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

function shortId(id: string) {
  if (id.length <= 18) return id;
  return `${id.slice(0, 8)}…${id.slice(-4)}`;
}

export function RecentRuns({
  runs,
  live,
  runner,
  completedIds,
}: {
  runs: FleetRunView[];
  live: FleetRunView | null;
  runner: string;
  completedIds: string[];
}) {
  const rows = live && !runs.some((run) => run.run_id === live.run_id) ? [live, ...runs] : runs;
  const visible = rows.slice(0, 12);

  return (
    <section aria-label="Recent runs" className="vf-card flex flex-col overflow-hidden rounded-lg">
      <header className="flex items-center justify-between border-b border-[#e8e6e3] px-4 py-3">
        <h2 className="text-[15px] font-medium tracking-tight text-[#111]">Recent runs</h2>
        <span className="text-[12px] text-[#6f6e69]">
          {runs.length} in session
          {live?.adk?.consult?.runner || runner ? ` · ${live?.adk?.consult?.runner || runner}` : ""}
        </span>
      </header>

      {visible.length === 0 ? (
        <p className="px-4 py-10 text-center text-[13px] text-[#6f6e69]">
          No runs yet — dispatch a fixture.
        </p>
      ) : (
        <ol className="max-h-[360px] divide-y divide-[#e8e6e3] overflow-y-auto" aria-live="polite">
          {visible.map((run) => {
            const queued = run.status === "QUEUED" || run.status === "RUNNING";
            const justCompleted = !queued && completedIds.includes(run.run_id);
            return (
              <li key={run.run_id} className="relative overflow-hidden px-4 py-3">
                {queued && (
                  <span className="pointer-events-none absolute inset-0" aria-hidden="true">
                    <span className="vf-scan-bar absolute inset-y-0 left-0 w-1/4 bg-emerald-400/20" />
                  </span>
                )}
                <div className="relative flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate font-mono text-[13px] font-medium text-[#111]">
                      {shortId(run.run_id)}
                    </p>
                    <p className="mt-0.5 flex min-w-0 flex-wrap items-center gap-1.5 text-[12px] text-[#6f6e69]">
                      {run.invoice_hash ? (
                        <HashReveal hash={run.invoice_hash} animate={justCompleted} />
                      ) : (
                        <span>{queued ? "awaiting hash" : "no hash"}</span>
                      )}
                      <span aria-hidden>·</span>
                      <span className="truncate">{run.reason}</span>
                    </p>
                  </div>
                  {queued ? (
                    <span className="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-[#e8e6e3] bg-[#f4f3f0] px-2 py-0.5 text-[11px] text-[#6f6e69]">
                      <Loader2 className="size-3 animate-spin" aria-hidden />
                      {run.status === "QUEUED" ? "queued" : run.status.toLowerCase()}
                    </span>
                  ) : (
                    <VerdictPill verdict={asVerdict(run.decision)} glow={justCompleted} />
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
