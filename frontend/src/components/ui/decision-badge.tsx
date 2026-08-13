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
        tone === "signed" && "bg-emerald-400/15 text-emerald-300 ring-1 ring-emerald-400/30",
        tone === "blocked" && "bg-rose-400/15 text-rose-300 ring-1 ring-rose-400/30",
        tone === "escalated" && "bg-amber-400/15 text-amber-200 ring-1 ring-amber-400/30",
        tone === "idle" && "bg-white/5 text-slate-400 ring-1 ring-white/10",
        pulse && tone !== "idle" && "vf-decision-pulse"
      )}
    >
      <span
        className={cn(
          "size-1.5 rounded-full",
          tone === "signed" && "bg-emerald-400 shadow-[0_0_8px_#34d399]",
          tone === "blocked" && "bg-rose-400 shadow-[0_0_8px_#fb7185]",
          tone === "escalated" && "bg-amber-300 shadow-[0_0_8px_#fbbf24]",
          tone === "idle" && "bg-slate-500"
        )}
      />
      {decision || "IDLE"}
    </span>
  );
}
