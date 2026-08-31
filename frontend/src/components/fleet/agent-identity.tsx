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
  const who = userId || "judge";
  const deniedText = denied.length ? denied.join(", ") : "none";

  return (
    <section aria-label="Agent identity" className="flex flex-wrap gap-1.5">
      <span className="vf-chip">{who}</span>
      <span className="vf-chip">
        {tenant} / {role}
      </span>
      <span className="vf-chip" title={allowed.join(", ") || "signing chain"}>
        {allowed.length ? `${allowed.length} tools` : "signing chain"}
      </span>
      <span className="vf-chip">denied {deniedText}</span>
    </section>
  );
}
