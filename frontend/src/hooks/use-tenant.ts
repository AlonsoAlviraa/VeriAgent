"use client";

/**
 * [FE-005] Tenant management hook.
 * Sincroniza el tenant activo (localStorage) con React y permite cambiarlo.
 * El header X-Tenant-Id se inyecta automáticamente vía apiClient.
 */

import { useCallback, useEffect, useState } from "react";
import { TENANT_STORAGE_KEY } from "@/lib/api-client";

export function useTenant() {
    const [tenantId, setTenantId] = useState<string>("default");

    // Cargar al montar (cliente).
    useEffect(() => {
        if (typeof window !== "undefined") {
            const stored = window.localStorage.getItem(TENANT_STORAGE_KEY);
            if (stored) setTenantId(stored);
        }
    }, []);

    // Escuchar cambios desde otras pestañas/componentes (ej. OrgSwitcher).
    useEffect(() => {
        const handler = (e: StorageEvent) => {
            if (e.key === TENANT_STORAGE_KEY && e.newValue) {
                setTenantId(e.newValue);
            }
        };
        window.addEventListener("storage", handler);
        return () => window.removeEventListener("storage", handler);
    }, []);

    const changeTenant = useCallback((id: string) => {
        setTenantId(id);
        if (typeof window !== "undefined") {
            window.localStorage.setItem(TENANT_STORAGE_KEY, id);
        }
    }, []);

    return { tenantId, changeTenant };
}
