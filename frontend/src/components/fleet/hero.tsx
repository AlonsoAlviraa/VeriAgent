import type { ReactNode } from "react";
import { verdictStyles, type Verdict } from "./verdict";
import { useCountUp } from "./use-count-up";

export type SettleSignal = { verdict: Verdict; tick: number };

function CounterTile({
  verdict,
  value,
  pulseKey,
}: {
  verdict: Verdict;
  value: number;
  pulseKey: number | null;
}) {
  const shown = useCountUp(value);
  const s = verdictStyles[verdict];

  return (
    <div className="relative overflow-hidden">
      {pulseKey !== null && (
        <span
          key={pulseKey}
          aria-hidden="true"
          className={`vf-ring pointer-events-none absolute inset-0 rounded-md border ${s.border} ${s.bg}`}
        />
      )}
      <dt className="vf-label relative">{verdict}</dt>
      <dd className={`relative mt-1 font-mono text-[28px] leading-none font-medium tabular-nums ${s.text}`}>
        {String(shown).padStart(2, "0")}
      </dd>
    </div>
  );
}

export function FleetHero({
  counters,
  lastSettled = null,
  kicker,
  title = "The LLM never writes the hash.",
  description = "Drop invoices. The fleet audits, signs, or escalates. Gemini 3.5 consults tighten-only. Tools own the hash.",
  actions,
}: {
  counters?: { signed: number; escalated: number; blocked: number };
  lastSettled?: SettleSignal | null;
  kicker?: string;
  title?: string;
  description?: string;
  actions?: ReactNode;
}) {
  const values: Record<Verdict, number> | null = counters
    ? {
        SIGNED: counters.signed,
        ESCALATED: counters.escalated,
        BLOCKED: counters.blocked,
      }
    : null;
  const order: Verdict[] = ["SIGNED", "ESCALATED", "BLOCKED"];

  return (
    <section className="border-b border-[#e8e6e3]">
      <div className="mx-auto flex w-full max-w-[1120px] flex-col gap-8 px-4 py-10 md:px-6 md:py-12 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-xl">
          {kicker ? <p className="vf-label mb-3">{kicker}</p> : null}
          <h1 className="text-[32px] leading-[1.15] font-medium tracking-[-0.03em] text-[#111] md:text-[40px]">
            {title}
          </h1>
          <p className="mt-3 max-w-lg text-[15px] leading-relaxed text-[#6f6e69]">
            {description}
          </p>
          <ul className="mt-4 flex flex-wrap gap-1.5">
            {["google-adk", "gemini-3.5-flash", "InMemoryRunner"].map((chip) => (
              <li key={chip} className="vf-chip h-7 text-[11px]">
                {chip}
              </li>
            ))}
          </ul>
          {actions ? <div className="mt-6 flex flex-wrap gap-3">{actions}</div> : null}
        </div>
        {values ? (
          <dl className="grid w-full grid-cols-3 gap-6 lg:w-auto lg:min-w-[280px]">
            {order.map((verdict) => (
              <CounterTile
                key={verdict}
                verdict={verdict}
                value={values[verdict]}
                pulseKey={lastSettled && lastSettled.verdict === verdict ? lastSettled.tick : null}
              />
            ))}
          </dl>
        ) : null}
      </div>
    </section>
  );
}
