"use client";

/**
 * PUX-05: Multi-org / tenant switcher surface.
 * Sets X-Tenant-Id for subsequent API calls via localStorage + callback.
 * The header injection itself happens in lib/api-client.ts.
 */

import React, { useEffect, useState } from "react";
import { useChainStatus } from "@/hooks/use-chain-status";

export type OrgOption = {
  id: string;
  name: string;
  plan?: string;
};

type Props = {
  orgs?: OrgOption[];
  value?: string;
  onChange?: (tenantId: string) => void;
};

const DEFAULT_ORGS: OrgOption[] = [
  { id: "default", name: "Default org", plan: "standard" },
];

export function OrgSwitcher({ orgs = DEFAULT_ORGS, value, onChange }: Props) {
  const [current, setCurrent] = useState(value || orgs[0]?.id || "default");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = window.localStorage.getItem("veriagent_tenant_id");
      if (stored) setCurrent(stored);
    }
  }, []);

  const select = (id: string) => {
    setCurrent(id);
    if (typeof window !== "undefined") {
      window.localStorage.setItem("veriagent_tenant_id", id);
    }
    onChange?.(id);
  };

  return (
    <div
      className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm"
      data-testid="org-switcher"
      role="group"
      aria-label="Organization switcher"
    >
      <span className="text-slate-500">Org</span>
      <select
        className="bg-transparent font-medium text-slate-100 outline-none"
        value={current}
        onChange={(e) => select(e.target.value)}
        data-testid="org-switcher-select"
      >
        {orgs.map((o) => (
          <option key={o.id} value={o.id}>
            {o.name}
            {o.plan ? ` (${o.plan})` : ""}
          </option>
        ))}
      </select>
    </div>
  );
}

export function ChainIntegrityBadge({
  tipHash,
  hasChain,
}: {
  tipHash?: string | null;
  hasChain?: boolean;
}) {
  return (
    <div
      className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] text-slate-300"
      data-testid="chain-integrity-status"
      data-has-chain={hasChain ? "true" : "false"}
    >
      Chain: {hasChain ? "active" : "empty"}
      {tipHash ? ` · tip ${tipHash.slice(0, 8)}…` : ""}
    </div>
  );
}

/**
 * ChainIntegrityBadgeLive: versión conectada que consulta el estado real de la
 * cadena de hashes del backend (GET /api/v1/chain/status).
 */
export function ChainIntegrityBadgeLive({
  issuerTaxId,
}: {
  issuerTaxId: string | null;
}) {
  const { data, isLoading, isError } = useChainStatus(issuerTaxId);

  if (isLoading) {
    return (
      <div
        className="rounded-full border border-white/10 px-2.5 py-1 text-[11px] text-slate-400"
        data-testid="chain-integrity-status"
      >
        Chain: consultando…
      </div>
    );
  }
  if (isError) {
    return (
      <div
        className="rounded-full border border-rose-400/30 px-2.5 py-1 text-[11px] text-rose-300"
        data-testid="chain-integrity-status"
        data-has-chain="false"
      >
        Chain: error de conexión
      </div>
    );
  }
  return (
    <ChainIntegrityBadge
      tipHash={data?.tip_hash ?? null}
      hasChain={!!data?.has_chain}
    />
  );
}

export default OrgSwitcher;
