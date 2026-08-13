import { asVerdict } from "./verdict";
import { Loader2 } from "lucide-react";
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
  const rows = live && !runs.some((run) => run.run_id === live.run_id) ? [live, ...runs] : runs;
  const visible = rows.slice(0, 12);

  return (
    <section aria-label="Recent runs" className="vf-card overflow-hidden rounded-lg">
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
        <>
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full min-w-[640px] text-left text-[13px]">
              <thead>
                <tr className="border-b border-[#e8e6e3] text-[11px] font-medium tracking-wide text-[#6f6e69] uppercase">
                  <th className="px-4 py-2.5 font-medium">Run</th>
                  <th className="px-4 py-2.5 font-medium">Decision</th>
                  <th className="px-4 py-2.5 font-medium">Reason</th>
                  <th className="px-4 py-2.5 font-medium">Hash</th>
                  <th className="px-4 py-2.5 font-medium">Armor</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((run, index) => {
                  const queued = run.status === "QUEUED" || run.status === "RUNNING";
                  const newest = index === 0 && live?.run_id === run.run_id;
                  return (
                    <tr
                      key={`${run.run_id}:${run.status}:${run.decision}`}
                      className={cn(
                        "border-b border-[#e8e6e3] last:border-0",
                        newest && "vf-enter"
                      )}
                    >
                      <td className="px-4 py-3 align-top font-mono text-[12px] text-[#6f6e69]">
                        {run.run_id.slice(0, 10)}
                      </td>
                      <td className="px-4 py-3 align-top">
                        {queued ? (
                          <QueuedMark status={run.status} />
                        ) : (
                          <VerdictPill verdict={asVerdict(run.decision)} />
                        )}
                      </td>
                      <td className="px-4 py-3 align-top text-[#111]">{run.reason}</td>
                      <td className="px-4 py-3 align-top font-mono text-[12px] text-[#6f6e69]">
                        {run.invoice_hash ? shortHash(run.invoice_hash) : "—"}
                      </td>
                      <td className="px-4 py-3 align-top text-[#6f6e69]">
                        {run.armor?.allowed === false ? "blocked" : queued ? run.status.toLowerCase() : "clean"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <ol className="divide-y divide-[#e8e6e3] md:hidden">
            {visible.map((run, index) => {
              const queued = run.status === "QUEUED" || run.status === "RUNNING";
              const newest = index === 0 && live?.run_id === run.run_id;
              return (
                <li
                  key={`${run.run_id}:${run.status}:${run.decision}`}
                  className={cn("flex flex-col gap-2 px-4 py-3", newest && "vf-enter")}
                >
                  <div className="flex items-start justify-between gap-3">
                    <p className="min-w-0 text-[13px] font-medium text-[#111]">{run.reason}</p>
                    {queued ? (
                      <QueuedMark status={run.status} />
                    ) : (
                      <VerdictPill verdict={asVerdict(run.decision)} />
                    )}
                  </div>
                  <p className="font-mono text-[12px] text-[#6f6e69]">
                    {run.invoice_hash ? shortHash(run.invoice_hash) : "no hash"}
                    {" · "}
                    {run.armor?.allowed === false ? "armor blocked" : queued ? run.status.toLowerCase() : "armor clean"}
                  </p>
                </li>
              );
            })}
          </ol>
        </>
      )}
    </section>
  );
}

function QueuedMark({ status }: { status: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-[#e8e6e3] bg-[#f4f3f0] px-2 py-0.5 text-[11px] text-[#6f6e69]">
      <Loader2 className="size-3 animate-spin" aria-hidden />
      {status === "QUEUED" ? "queued" : status.toLowerCase()}
    </span>
  );
}
