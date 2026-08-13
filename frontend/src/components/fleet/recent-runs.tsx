"use client";

import { Loader2 } from "lucide-react";
import { asVerdict } from "./verdict";
import { shortHash, VerdictPill } from "./verdict-pill";
import { useLocale } from "@/components/i18n/locale-provider";

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
}: {
  runs: FleetRunView[];
  live: FleetRunView | null;
}) {
  const { t } = useLocale();
  const rows = live && !runs.some((run) => run.run_id === live.run_id) ? [live, ...runs] : runs;
  const visible = rows.slice(0, 12);

  return (
    <section aria-label={t("recent.aria")} className="vf-card overflow-hidden rounded-lg">
      <header className="flex items-center justify-between border-b border-[#e8e6e3] px-4 py-3">
        <h2 className="text-[15px] font-medium tracking-tight text-[#111]">{t("recent.title")}</h2>
        <span className="text-[12px] text-[#6f6e69]">{t("recent.inSession", { n: runs.length })}</span>
      </header>

      {visible.length === 0 ? (
        <p className="px-4 py-10 text-center text-[13px] text-[#6f6e69]">
          {t("recent.empty")}
        </p>
      ) : (
        <>
          <div className="hidden overflow-x-auto sm:block">
            <table className="w-full text-left text-[13px]">
              <thead>
                <tr className="border-b border-[#e8e6e3] text-[11px] font-medium tracking-wide text-[#6f6e69] uppercase">
                  <th className="px-4 py-2.5 font-medium">{t("recent.run")}</th>
                  <th className="px-4 py-2.5 font-medium">{t("recent.verdict")}</th>
                  <th className="px-4 py-2.5 font-medium">{t("recent.hash")}</th>
                  <th className="px-4 py-2.5 font-medium">{t("recent.reason")}</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((run, index) => {
                  const queued = run.status === "QUEUED" || run.status === "RUNNING";
                  return (
                    <tr
                      key={run.run_id}
                      className={`border-b border-[#e8e6e3] last:border-0 ${index === 0 && live?.run_id === run.run_id ? "vf-enter" : ""}`}
                    >
                      <td className="px-4 py-3 font-mono text-[12px] text-[#6f6e69]">{shortId(run.run_id)}</td>
                      <td className="px-4 py-3">
                        {queued ? (
                          <span className="inline-flex items-center gap-1.5 text-[12px] text-[#6f6e69]">
                            <Loader2 className="size-3 animate-spin" aria-hidden />
                            {t("recent.settling")}
                          </span>
                        ) : (
                          <VerdictPill verdict={asVerdict(run.decision)} />
                        )}
                      </td>
                      <td className="px-4 py-3 font-mono text-[12px] text-[#6f6e69]">
                        {run.invoice_hash ? shortHash(run.invoice_hash) : "—"}
                      </td>
                      <td className="px-4 py-3 text-[#111]">{run.reason}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <ol className="divide-y divide-[#e8e6e3] sm:hidden">
            {visible.map((run, index) => {
              const queued = run.status === "QUEUED" || run.status === "RUNNING";
              return (
                <li
                  key={run.run_id}
                  className={`flex items-start justify-between gap-3 px-4 py-3 ${index === 0 && live?.run_id === run.run_id ? "vf-enter" : ""}`}
                >
                  <div className="min-w-0">
                    <p className="font-mono text-[13px] font-medium text-[#111]">{shortId(run.run_id)}</p>
                    <p className="mt-0.5 truncate text-[12px] text-[#6f6e69]">
                      {run.invoice_hash ? shortHash(run.invoice_hash) : queued ? t("recent.settling") : t("recent.noHash")}
                      {" · "}
                      {run.reason}
                    </p>
                  </div>
                  {queued ? (
                    <Loader2 className="size-4 shrink-0 animate-spin text-[#6f6e69]" />
                  ) : (
                    <VerdictPill verdict={asVerdict(run.decision)} />
                  )}
                </li>
              );
            })}
          </ol>
        </>
      )}
    </section>
  );
}
