import { cn } from "@/lib/utils";

export function decisionTone(decision?: string) {
  if (decision === "SIGNED") return "signed";
  if (decision === "BLOCKED" || decision === "REJECTED") return "blocked";
  if (decision === "ESCALATED") return "escalated";
  return "idle";
}

export function DecisionBadge({
  decision,
  size = "md",
  pulse = false,
}: {
  decision?: string;
  size?: "sm" | "md" | "lg";
  pulse?: boolean;
}) {
  const tone = decisionTone(decision);
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full font-semibold uppercase tracking-[0.14em]",
        size === "sm" && "px-2 py-0.5 text-[10px]",
        size === "md" && "px-2.5 py-1 text-[11px]",
        size === "lg" && "px-3.5 py-1.5 text-xs",
        tone === "signed" && "border border-[#c8e6d3] bg-[#eef8f1] text-[#17663f]",
        tone === "blocked" && "border border-[#f0c7c3] bg-[#fbefee] text-[#9b2c2c]",
        tone === "escalated" && "border border-[#f3d5b0] bg-[#fbf3e8] text-[#9a4d09]",
        tone === "idle" && "border border-[#e8e6e3] bg-[#f4f3f0] text-[#6f6e69]"
      )}
    >
      {decision || "IDLE"}
    </span>
  );
}
