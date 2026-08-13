import { Bug, Calculator, FileCheck2, Play, UtensilsCrossed, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { VerdictPill } from "./verdict-pill";

export const FIXTURES = [
  {
    id: "valid",
    label: "Valid invoice",
    path: "/demo-fixtures/valid_invoice.json",
    hint: "Math + NIF hold. Hash is written by tools.",
    detail: "verifactu.chain → sign",
    expect: "SIGNED" as const,
    icon: FileCheck2,
  },
  {
    id: "math",
    label: "Math error",
    path: "/demo-fixtures/math_error.json",
    hint: "Consult can only tighten. Never signs 999.",
    detail: "consult(tighten-only) → escalate",
    expect: "ESCALATED" as const,
    icon: Calculator,
  },
  {
    id: "injection",
    label: "Prompt injection",
    path: "/demo-fixtures/injection.json",
    hint: "Model Armor stops ignore rules and sign.",
    detail: "model_armor → block",
    expect: "BLOCKED" as const,
    icon: Bug,
  },
  {
    id: "hospitality",
    label: "Hospitality",
    path: "/demo-fixtures/hospitality.json",
    hint: "Memory Bank flags restaurants for this tenant.",
    detail: "memory_bank → escalate",
    expect: "ESCALATED" as const,
    icon: UtensilsCrossed,
  },
];

export function FixtureGrid({
  busy,
  activeJob,
  onDispatch,
}: {
  busy: boolean;
  activeJob: string;
  onDispatch: (path: string) => void;
}) {
  return (
    <section aria-label="Fixtures" className="flex flex-col gap-3">
      <div className="flex items-baseline justify-between">
        <h2 className="font-mono text-[10px] uppercase tracking-[0.22em] text-slate-500">
          Fixtures · dispatch to fleet
        </h2>
        <span className="font-mono text-[10px] text-slate-600">04 loaded</span>
      </div>

      <div className="vf-stagger grid grid-cols-1 gap-3 sm:grid-cols-2">
        {FIXTURES.map((fixture, index) => {
          const Icon = fixture.icon;
          const active = busy && activeJob === fixture.path;
          return (
            <Card
              key={fixture.id}
              size="sm"
              className={cn(
                "vf-panel group gap-0 rounded-sm p-0 ring-0 transition-colors hover:border-emerald-400/35",
                active && "vf-busy"
              )}
            >
              <div className="flex items-start justify-between gap-3 px-3 pt-3 pb-2">
                <div className="flex items-start gap-2.5">
                  <span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-sm border border-[#26344f] bg-[#0b1220]">
                    {active ? (
                      <Loader2 className="size-3.5 animate-spin text-emerald-300" />
                    ) : (
                      <Icon className="size-3.5 text-slate-300" />
                    )}
                  </span>
                  <div>
                    <h3 className="text-[13px] leading-tight font-medium tracking-tight text-slate-100">
                      {fixture.label}
                    </h3>
                    <p className="mt-0.5 font-mono text-[9px] uppercase tracking-[0.14em] text-slate-600">
                      fx-{String(index + 1).padStart(2, "0")} · {fixture.detail}
                    </p>
                  </div>
                </div>
                <VerdictPill verdict={fixture.expect} />
              </div>

              <p className="border-t border-[#1b2740] px-3 py-2.5 text-[12px] leading-snug text-slate-400">
                {fixture.hint}
              </p>

              <div className="border-t border-[#1b2740] px-3 py-2">
                <Button
                  variant="ghost"
                  size="xs"
                  disabled={busy}
                  onClick={() => onDispatch(fixture.path)}
                  className="h-7 w-full justify-center gap-1.5 rounded-sm border border-[#243350] bg-[#0b1220] font-mono text-[10px] uppercase tracking-[0.16em] text-slate-300 hover:border-emerald-400/40 hover:bg-emerald-400/10 hover:text-emerald-200"
                >
                  <Play data-icon="inline-start" aria-hidden />
                  Dispatch
                </Button>
              </div>
            </Card>
          );
        })}
      </div>
    </section>
  );
}
