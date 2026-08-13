import { Ban, KeyRound } from "lucide-react";

export function AgentIdentity({
  tenant,
  role,
  userId,
  allowed,
  denied,
}: {
  tenant: string;
  role: string;
  userId?: string;
  allowed: string[];
  denied: string[];
}) {
  return (
    <section aria-label="Agent identity" className="vf-panel rounded-sm">
      <header className="flex items-center justify-between border-b border-[#1b2740] px-3 py-2.5">
        <h2 className="font-mono text-[10px] uppercase tracking-[0.22em] text-slate-500">
          Agent identity
        </h2>
        <span className="font-mono text-[10px] text-slate-400">
          {tenant} / {role}
        </span>
      </header>

      <div className="flex flex-col gap-3 px-3 py-3">
        <div>
          <p className="flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-[0.16em] text-slate-600">
            <KeyRound className="size-3" aria-hidden />
            Granted tools
          </p>
          <ul className="mt-2 flex flex-wrap gap-1.5">
            {(allowed.length ? allowed : ["—"]).map((tool) => (
              <li
                key={tool}
                className="rounded-sm border border-[#243350] bg-[#0b1220] px-1.5 py-0.5 font-mono text-[10px] text-slate-300"
              >
                {tool}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <p className="flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-[0.16em] text-slate-600">
            <Ban className="size-3" aria-hidden />
            Denied tools
          </p>
          {denied.length === 0 ? (
            <p className="mt-2 font-mono text-[10px] text-slate-500">
              none — issuer holds full signing chain
            </p>
          ) : (
            <ul className="mt-2 flex flex-wrap gap-1.5">
              {denied.map((tool) => (
                <li
                  key={tool}
                  className="rounded-sm border border-rose-400/35 bg-rose-400/10 px-1.5 py-0.5 font-mono text-[10px] text-rose-300 line-through decoration-rose-400/50"
                >
                  {tool}
                </li>
              ))}
            </ul>
          )}
        </div>

        <p className="border-t border-[#161f33] pt-2.5 text-[11px] leading-snug text-slate-500">
          {userId ? `${userId} · ` : ""}
          {role === "auditor"
            ? "Auditor identity cannot sign or write hashes — valid invoices escalate for issuer countersign."
            : "Issuer identity may invoke the chaining and signing tools. The model still never writes the hash."}
        </p>
      </div>
    </section>
  );
}
