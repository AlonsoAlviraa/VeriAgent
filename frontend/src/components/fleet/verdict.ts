export type Verdict = "SIGNED" | "ESCALATED" | "BLOCKED";

export const verdictStyles: Record<
  Verdict,
  { text: string; border: string; bg: string; dot: string }
> = {
  SIGNED: {
    text: "text-emerald-300",
    border: "border-emerald-400/40",
    bg: "bg-emerald-400/10",
    dot: "bg-emerald-400",
  },
  ESCALATED: {
    text: "text-amber-300",
    border: "border-amber-400/40",
    bg: "bg-amber-400/10",
    dot: "bg-amber-400",
  },
  BLOCKED: {
    text: "text-rose-300",
    border: "border-rose-400/40",
    bg: "bg-rose-400/10",
    dot: "bg-rose-400",
  },
};

export function asVerdict(decision?: string): Verdict {
  if (decision === "SIGNED") return "SIGNED";
  if (decision === "BLOCKED" || decision === "REJECTED") return "BLOCKED";
  return "ESCALATED";
}
