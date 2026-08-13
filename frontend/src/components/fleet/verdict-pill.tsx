import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { asVerdict, verdictStyles, type Verdict } from "./verdict";

export function VerdictPill({
  verdict,
  glow = false,
}: {
  verdict?: string;
  glow?: boolean;
}) {
  const key: Verdict = asVerdict(verdict);
  const s = verdictStyles[key];
  return (
    <Badge
      variant="outline"
      className={cn(
        "relative h-auto rounded-md border px-2 py-0.5 text-[11px] font-medium tracking-normal",
        s.border,
        s.bg,
        s.text
      )}
    >
      {glow && (
        <span
          aria-hidden="true"
          className={cn("vf-ring pointer-events-none absolute -inset-px rounded-full border", s.border, s.bg)}
        />
      )}
      <span className="relative">{verdict || key}</span>
    </Badge>
  );
}
