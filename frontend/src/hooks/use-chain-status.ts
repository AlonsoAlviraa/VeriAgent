"use client";

/**
 * [FE-006] Hook para consultar el estado de la cadena de hashes del tenant.
 * Consume GET /api/v1/chain/status?issuer_tax_id=... (PUX-05).
 * Refresca cuando cambia el tenant o el emisor.
 */

import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api-client";

export type ChainStatus = {
    tenant_id: string;
    issuer_tax_id: string;
    tip_hash: string | null;
    has_chain: boolean;
    integrity: string;
};

export function useChainStatus(issuerTaxId: string | null, enabled = true) {
    return useQuery({
        queryKey: ["chain-status", issuerTaxId],
        queryFn: async () => {
            const response = await apiClient.get<ChainStatus>(
                "/api/v1/chain/status",
                { params: { issuer_tax_id: issuerTaxId } }
            );
            return response.data;
        },
        enabled: !!issuerTaxId && enabled,
        staleTime: 15_000,
        retry: 1,
    });
}
