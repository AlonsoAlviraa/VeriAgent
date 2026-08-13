import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { asVerdict, verdictStyles, type Verdict } from "./verdict";

export function VerdictPill({ verdict }: { verdict?: string }) {
  const key: Verdict = asVerdict(verdict);
  const s = verdictStyles[key];
  return (
    <Badge
      variant="outline"
      className={cn(
        "h-auto rounded-md border px-2 py-0.5 text-[11px] font-medium tracking-normal",
        s.border,
        s.bg,
        s.text
      )}
    >
      {verdict || key}
    </Badge>
  );
}

export function shortHash(hash: string) {
  if (hash.length <= 20) return hash;
  return `${hash.slice(0, 8)}…${hash.slice(-8)}`;
}
