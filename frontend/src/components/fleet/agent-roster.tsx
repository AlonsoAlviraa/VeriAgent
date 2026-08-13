"use client";

import { useLocale } from "@/components/i18n/locale-provider";
import type { MessageKey } from "@/lib/i18n";

export type RosterAgent = {
  agent_id: string;
  name: string;
  version: string;
  role: string;
  tools?: string[];
  model?: string;
  status?: string;
};

const JOB_KEYS: Record<string, MessageKey> = {
  ingestion: "roster.job.ingestion",
  fiscal_auditor: "roster.job.fiscal_auditor",
  signer: "roster.job.signer",
  escalation: "roster.job.escalation",
};

export function jobLabel(agentId: string, t: (key: MessageKey) => string): string {
  const key = JOB_KEYS[agentId];
  return key ? t(key) : agentId;
}

export function AgentRoster({
  agents,
  compact = false,
}: {
  agents: RosterAgent[] | null;
  compact?: boolean;
}) {
  const { t } = useLocale();
  const loaded = Array.isArray(agents) && agents.length > 0;

  return (
    <section aria-label={t("roster.kicker")} className={compact ? "" : "border-b border-[#e8e6e3]"}>
      <div className={compact ? "" : "mx-auto w-full max-w-[1120px] px-4 py-10 md:px-6 md:py-14"}>
        <p className="vf-label">{t("roster.kicker")}</p>
        {compact ? null : (
          <h2 className="mt-2 text-[18px] font-medium tracking-tight text-[#111] md:text-[22px]">
            {t("roster.title")}
          </h2>
        )}
        {loaded ? (
          <ul className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {agents.map((agent) => (
              <li key={agent.agent_id} className="vf-card rounded-lg p-4">
                <p className="vf-label">{jobLabel(agent.agent_id, t)}</p>
                <p className="mt-1 text-[14px] font-medium tracking-tight text-[#111]">{agent.name}</p>
                <p className="mt-0.5 font-mono text-[11px] text-[#6f6e69]">v{agent.version}</p>
                {compact ? null : (
                  <p className="mt-2 text-[12px] leading-relaxed text-[#6f6e69]">{agent.role}</p>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-4 max-w-[560px] text-sm leading-relaxed text-[#6f6e69]">{t("roster.offline")}</p>
        )}
      </div>
    </section>
  );
}
