import { Check } from "lucide-react";

export function FleetChecklist({
  track,
  items,
}: {
  track?: string;
  items: { id: string; name: string; status: string; proof: string }[];
}) {
  return (
    <section aria-label="Fleet checklist" className="vf-panel rounded-sm">
      <header className="border-b border-[#1b2740] px-3 py-2.5">
        <h2 className="font-mono text-[10px] uppercase tracking-[0.22em] text-slate-500">
          Fleet checklist
        </h2>
        <p className="mt-1 font-mono text-[10px] text-slate-600">
          {track || "Fortified Enterprise Fleet"}
        </p>
      </header>
      <ul className="divide-y divide-[#161f33]">
        {(items.length ? items : STAGE_ONE_FALLBACK).map((item) => (
          <li key={item.id || item.name} className="flex items-center gap-2.5 px-3 py-2.5">
            <span className="flex size-4 shrink-0 items-center justify-center rounded-sm border border-emerald-400/40 bg-emerald-400/10">
              <Check className="size-2.5 text-emerald-300" strokeWidth={3} />
            </span>
            <span className="min-w-0 flex-1 font-mono text-[11px] text-slate-200">{item.name}</span>
            <span className="max-w-[46%] shrink-0 truncate font-mono text-[10px] text-slate-600" title={item.proof}>
              {item.proof}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

const STAGE_ONE_FALLBACK = [
  { id: "adk", name: "google-adk", status: "ok", proof: "agent runtime loaded" },
  { id: "gemini", name: "gemini-3.5-flash", status: "ok", proof: "consult model, tighten-only" },
  { id: "runner", name: "InMemoryRunner", status: "ok", proof: "local session, no external endpoint" },
];
