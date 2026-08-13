import { verdictStyles, type Verdict } from "./verdict";

export function FleetHero({
  counters,
}: {
  counters: { signed: number; escalated: number; blocked: number };
}) {
  const values: Record<Verdict, number> = {
    SIGNED: counters.signed,
    ESCALATED: counters.escalated,
    BLOCKED: counters.blocked,
  };
  const order: Verdict[] = ["SIGNED", "ESCALATED", "BLOCKED"];

  return (
    <section className="relative overflow-hidden border-b border-[#1e2b45]">
      <div className="vf-grid absolute inset-0" aria-hidden />
      <div className="vf-scanline absolute inset-0" aria-hidden />
      <div
        className="pointer-events-none absolute top-0 -left-24 size-56 rounded-full bg-emerald-500/10 blur-3xl"
        aria-hidden
      />
      <div className="relative mx-auto flex w-full max-w-[1280px] flex-col gap-8 px-4 py-10 md:px-6 md:py-12 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-2xl">
          <p className="font-mono text-[10px] uppercase tracking-[0.32em] text-emerald-300/80">
            JUDGE CONSOLE · NO CHAT
          </p>
          <h1 className="mt-4 text-[34px] leading-[1.05] font-semibold tracking-[-0.03em] text-slate-50 md:text-[46px]">
            The LLM never writes the hash.
          </h1>
          <p className="mt-4 max-w-xl text-[13px] leading-relaxed text-slate-400 md:text-sm">
            Drop invoices. The fleet audits, signs, or escalates. Gemini 3.5 consults
            tighten-only. Tools own the hash.
          </p>
        </div>
        <dl className="vf-stagger grid w-full grid-cols-3 gap-2 lg:w-auto">
          {order.map((verdict) => {
            const s = verdictStyles[verdict];
            return (
              <div
                key={verdict}
                className={`vf-panel vf-kpi rounded-sm px-3 py-3 lg:w-[128px] ${
                  verdict === "SIGNED" ? "border-emerald-400/25" : ""
                }`}
              >
                <dt className="flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-[0.16em] text-slate-500">
                  <span className={`size-1 rounded-full ${s.dot}`} aria-hidden />
                  {verdict}
                </dt>
                <dd
                  className={`mt-2 font-mono text-2xl leading-none font-medium tabular-nums ${s.text} ${
                    verdict === "SIGNED" ? "vf-glow-text" : ""
                  }`}
                >
                  {String(values[verdict]).padStart(2, "0")}
                </dd>
              </div>
            );
          })}
        </dl>
      </div>
    </section>
  );
}
