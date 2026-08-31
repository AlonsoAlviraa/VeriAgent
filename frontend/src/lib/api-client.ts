import axios, { AxiosHeaders } from "axios";
import { t, type Locale } from "./i18n";

/**
 * Same-origin axios. Next app/api/v1/[...path] proxies to 127.0.0.1:8000.
 * Never omit wait=false. Never clobber an explicit X-Tenant-Id.
 */

export const TENANT_STORAGE_KEY = "veriagent_tenant_id";

/** Lee el tenant activo desde localStorage (safe para SSR). */
export function getActiveTenant(): string | null {
    if (typeof window === "undefined") return null;
    return window.localStorage.getItem(TENANT_STORAGE_KEY);
}

export function formatApiError(error: unknown, locale: Locale = "es"): string {
    const err = error as { message?: string; response?: { status?: number; data?: { detail?: string; message?: string } }; code?: string };
    if (!err?.response) {
        return t(locale, "error.network");
    }
    return err.response.data?.detail || err.response.data?.message || err.message || t(locale, "error.requestFailed");
}

const apiClient = axios.create({
    baseURL: "",
    headers: {
        "Content-Type": "application/json",
    },
    paramsSerializer: {
        serialize(params) {
            const search = new URLSearchParams();
            for (const [key, value] of Object.entries(params || {})) {
                if (value === undefined || value === null) continue;
                if (value === true || value === false) {
                    search.set(key, value ? "true" : "false");
                    continue;
                }
                search.set(key, String(value));
            }
            return search.toString();
        },
    },
});

apiClient.interceptors.request.use((config) => {
    const headers = AxiosHeaders.from(config.headers);
    if (!headers.get("X-Tenant-Id")) {
        const tenantId = getActiveTenant();
        if (tenantId) headers.set("X-Tenant-Id", tenantId);
    }
    config.headers = headers;
    return config;
});

apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (!error.response) {
            console.error("CRITICAL: El servidor no responde o no está disponible.");
        } else {
            const message = error.response.data?.detail || error.response.data?.message || "Error desconocido";
            console.warn(`API Error [${error.response.status}]: ${message}`);
        }
        return Promise.reject(error);
    }
);

export default apiClient;
