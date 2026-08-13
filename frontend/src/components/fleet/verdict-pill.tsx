import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { asVerdict, verdictStyles, type Verdict } from "./verdict";

export function VerdictPill({
  verdict,
  glow = false,
  pulse = false,
}: {
  verdict?: string;
  glow?: boolean;
  pulse?: boolean;
}) {
  const key: Verdict = asVerdict(verdict);
  const s = verdictStyles[key];
  return (
    <Badge
      variant="outline"
      className={cn(
        "h-auto gap-1.5 rounded-sm border px-2 py-0.5 font-mono text-[10px] font-medium uppercase tracking-[0.14em]",
        s.border,
        s.bg,
        s.text,
        glow && key === "SIGNED" && "vf-glow",
        pulse && "vf-decision-pulse"
      )}
    >
      <span className={cn("size-1.5 rounded-full", s.dot)} aria-hidden />
      {verdict || key}
    </Badge>
  );
}
