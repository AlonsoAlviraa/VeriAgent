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
  const deniedText = denied.length ? `denied ${denied.join(", ")}` : "no denied tools";
  const granted = allowed.length ? allowed.join(", ") : "signing chain";

  return (
    <p className="text-[12px] leading-relaxed text-[#6f6e69]">
      {who} · {tenant} / {role} · {granted} · {deniedText}
      {role === "auditor"
        ? " · auditor cannot sign or write hashes"
        : " · the model still never writes the hash"}
    </p>
  );
}
