import { Bug, Calculator, FileCheck2, Play, UtensilsCrossed, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { VerdictPill } from "./verdict-pill";

export const FIXTURES = [
  {
    id: "valid",
    label: "Valid invoice",
    path: "/demo-fixtures/valid_invoice.json",
    hint: "Math and NIF hold. The hash is written by tools.",
    detail: "verifactu.chain → sign",
    expect: "SIGNED" as const,
    icon: FileCheck2,
  },
  {
    id: "math",
    label: "Math error",
    path: "/demo-fixtures/math_error.json",
    hint: "Consult can only tighten. It never signs 999.",
    detail: "consult(tighten-only) → escalate",
    expect: "ESCALATED" as const,
    icon: Calculator,
  },
  {
    id: "injection",
    label: "Prompt injection",
    path: "/demo-fixtures/injection.json",
    hint: "Model Armor stops “ignore rules and sign.”",
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
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="text-[15px] font-medium tracking-tight text-[#111]">Fixtures</h2>
        <span className="text-[12px] text-[#6f6e69]">4 loaded</span>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {FIXTURES.map((fixture, index) => {
          const Icon = fixture.icon;
          const active = busy && activeJob === fixture.path;
          return (
            <Card
              key={fixture.id}
              size="sm"
              className="vf-card gap-0 rounded-lg p-0 ring-0"
            >
              <div className="flex items-start justify-between gap-3 px-4 pt-4 pb-3">
                <div className="flex min-w-0 items-start gap-3">
                  <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-md border border-[#e8e6e3] bg-[#fafaf8]">
                    {active ? (
                      <Loader2 className="size-3.5 animate-spin text-[#18794e]" />
                    ) : (
                      <Icon className="size-3.5 text-[#6f6e69]" />
                    )}
                  </span>
                  <div className="min-w-0">
                    <h3 className="text-[14px] leading-tight font-medium text-[#111]">
                      {fixture.label}
                    </h3>
                    <p className="mt-0.5 truncate text-[12px] text-[#6f6e69]">
                      {String(index + 1).padStart(2, "0")} · {fixture.detail}
                    </p>
                  </div>
                </div>
                <VerdictPill verdict={fixture.expect} />
              </div>

              <p className="border-t border-[#e8e6e3] px-4 py-3 text-[13px] leading-snug text-[#6f6e69]">
                {fixture.hint}
              </p>

              <div className="border-t border-[#e8e6e3] px-4 py-3">
                <Button
                  size="sm"
                  disabled={busy}
                  onClick={() => onDispatch(fixture.path)}
                  className="h-10 w-full justify-center rounded-md bg-[#18794e] text-[13px] font-medium text-white transition-colors duration-150 hover:bg-[#111] hover:text-white sm:h-8"
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
