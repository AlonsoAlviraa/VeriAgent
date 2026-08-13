import type { ReactNode } from "react";
import { verdictStyles, type Verdict } from "./verdict";

export function FleetHero({
  counters,
  kicker,
  title = "The LLM never writes the hash.",
  subtitleEs,
  description = "Dispatch a fixture. The fleet signs, escalates, or blocks — consult can only tighten.",
  actions,
}: {
  counters?: { signed: number; escalated: number; blocked: number };
  kicker?: string;
  title?: string;
  subtitleEs?: string;
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
          {kicker ? <p className="mb-3 text-[13px] text-[#6f6e69]">{kicker}</p> : null}
          <h1 className="text-[32px] leading-[1.15] font-medium tracking-[-0.03em] text-[#111] md:text-[40px]">
            {title}
          </h1>
          {subtitleEs ? (
            <p className="mt-2 text-[16px] leading-snug text-[#6f6e69]">{subtitleEs}</p>
          ) : null}
          <p className="mt-3 max-w-lg text-[15px] leading-relaxed text-[#6f6e69]">
            {description}
          </p>
          {actions ? <div className="mt-6 flex flex-wrap gap-3">{actions}</div> : null}
        </div>
        {values ? (
          <dl className="grid w-full grid-cols-3 gap-6 lg:w-auto lg:min-w-[280px]">
            {order.map((verdict) => {
              const s = verdictStyles[verdict];
              return (
                <div key={verdict}>
                  <dt className="vf-label">{verdict}</dt>
                  <dd className={`mt-1 font-mono text-[28px] leading-none font-medium tabular-nums ${s.text}`}>
                    {String(values[verdict]).padStart(2, "0")}
                  </dd>
                </div>
              );
            })}
          </dl>
        ) : null}
      </div>
    </section>
  );
}
