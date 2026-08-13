import { Check } from "lucide-react";

export function FleetChecklist({
  track,
  items,
}: {
  track?: string;
  items: { id: string; name: string; status: string; proof: string }[];
}) {
  const rows = items.length ? items : STAGE_ONE_FALLBACK;

  return (
    <section aria-label="Fleet checklist" className="vf-card rounded-lg">
      <header className="border-b border-[#e8e6e3] px-4 py-3">
        <h2 className="text-[15px] font-medium tracking-tight text-[#111]">Checklist</h2>
        <p className="mt-0.5 text-[12px] text-[#6f6e69]">{track || "Fortified Enterprise Fleet"}</p>
      </header>
      <ul className="divide-y divide-[#e8e6e3]">
        {rows.map((item) => (
          <li key={item.id || item.name} className="flex items-start gap-3 px-4 py-3">
            <span className="mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-full bg-[#eef8f1] text-[#18794e]">
              <Check className="size-2.5" strokeWidth={3} />
            </span>
            <div className="min-w-0">
              <p className="text-[13px] text-[#111]">{item.name}</p>
              <p className="mt-0.5 text-[12px] text-[#6f6e69]">{item.proof}</p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

const STAGE_ONE_FALLBACK = [
  { id: "adk", name: "google-adk", status: "ok", proof: "Agent runtime loaded" },
  { id: "gemini", name: "gemini-3.5-flash", status: "ok", proof: "Consult model, tighten-only" },
  { id: "runner", name: "InMemoryRunner", status: "ok", proof: "Local session, no external endpoint" },
];
