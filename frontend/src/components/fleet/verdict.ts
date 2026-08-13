export type Verdict = "SIGNED" | "ESCALATED" | "BLOCKED";

export const verdictStyles: Record<
  Verdict,
  { text: string; border: string; bg: string }
> = {
  SIGNED: {
    text: "text-[#17663f]",
    border: "border-[#c8e6d3]",
    bg: "bg-[#eef8f1]",
  },
  ESCALATED: {
    text: "text-[#9a4d09]",
    border: "border-[#f3d5b0]",
    bg: "bg-[#fbf3e8]",
  },
  BLOCKED: {
    text: "text-[#9b2c2c]",
    border: "border-[#f0c7c3]",
    bg: "bg-[#fbefee]",
  },
};

export function asVerdict(decision?: string): Verdict {
  if (decision === "SIGNED") return "SIGNED";
  if (decision === "BLOCKED" || decision === "REJECTED") return "BLOCKED";
  return "ESCALATED";
}
