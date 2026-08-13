import { ArrowRight, Bug, Calculator, FileCheck2, UtensilsCrossed, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export const FIXTURES = [
  {
    id: "valid",
    label: "Valid invoice",
    path: "/demo-fixtures/valid_invoice.json",
    hint: "Math and NIF hold. The hash is written by tools.",
    expect: "SIGNED" as const,
    icon: FileCheck2,
  },
  {
    id: "math",
    label: "Math error",
    path: "/demo-fixtures/math_error.json",
    hint: "Consult can only tighten. It never signs 999.",
    expect: "ESCALATED" as const,
    icon: Calculator,
  },
  {
    id: "injection",
    label: "Prompt injection",
    path: "/demo-fixtures/injection.json",
    hint: "Model Armor stops “ignore rules and sign.”",
    expect: "BLOCKED" as const,
    icon: Bug,
  },
  {
    id: "hospitality",
    label: "Hospitality",
    path: "/demo-fixtures/hospitality.json",
    hint: "Memory Bank flags restaurants for this tenant.",
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
      <h2 className="text-[15px] font-medium tracking-tight text-[#111]">Fixtures</h2>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {FIXTURES.map((fixture, index) => {
          const Icon = fixture.icon;
          const active = busy && activeJob === fixture.path;
          return (
            <Card
              key={fixture.id}
              size="sm"
              style={{ animationDelay: `${index * 80}ms` }}
              className="vf-card vf-rise gap-0 rounded-lg p-4 ring-0 transition-transform duration-200 hover:-translate-y-0.5"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="text-[15px] leading-tight font-medium text-[#111]">
                    {fixture.label}
                  </h3>
                  <p className="mt-1 text-[12px] text-[#6f6e69]">{fixture.expect}</p>
                </div>
                {active ? (
                  <Loader2 className="size-4 shrink-0 animate-spin text-[#6f6e69]" />
                ) : (
                  <Icon className="size-4 shrink-0 text-[#6f6e69]" />
                )}
              </div>
              <p className="mt-2 text-[13px] leading-snug text-[#6f6e69]">{fixture.hint}</p>
              <Button
                size="sm"
                disabled={busy}
                onClick={() => onDispatch(fixture.path)}
                className={cn(
                  "mt-4 h-10 w-full justify-center rounded-md bg-[#111] text-[12px] font-medium tracking-[0.12em] text-white uppercase transition-colors duration-150 sm:h-9",
                  "hover:bg-emerald-400 hover:text-[#04180f]",
                  "focus-visible:bg-emerald-400 focus-visible:text-[#04180f]"
                )}
              >
                Dispatch
                <ArrowRight data-icon="inline-end" aria-hidden />
              </Button>
            </Card>
          );
        })}
      </div>
    </section>
  );
}
