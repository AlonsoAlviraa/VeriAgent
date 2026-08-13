import axios from "axios";
import { t, type Locale } from "./i18n";

/**
 * [FE-002] Configured Axios instance for VeriAgent Backend.
 * Handles base URL, tenant routing and generic network errors.
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

function readHeader(headers: unknown, name: string): string {
    if (!headers || typeof headers !== "object") return "";
    const bag = headers as { get?: (key: string) => unknown; [key: string]: unknown };
    const fromGet = typeof bag.get === "function" ? bag.get(name) : undefined;
    const value = fromGet ?? bag[name] ?? bag[name.toLowerCase()];
    return value == null ? "" : String(value);
}

const apiClient = axios.create({
    // Same-origin so the browser does not hit :8000 (CORS). Next proxies /api/v1 → 127.0.0.1:8000.
    baseURL: "",
    headers: {
        "Content-Type": "application/json",
    },
});

// Request Interceptor: inyecta X-Tenant-Id en cada llamada (PUX-05).
apiClient.interceptors.request.use((config) => {
    const tenantId = getActiveTenant();
    if (tenantId) {
        config.headers = config.headers ?? {};
        if (!readHeader(config.headers, "X-Tenant-Id")) {
            config.headers["X-Tenant-Id"] = tenantId;
        }
    }
    return config;
});

// Response Interceptor for Global Error Handling
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (!error.response) {
            // Network Error (server down, CORS, etc.)
            console.error("CRITICAL: El servidor no responde o no está disponible.");
        } else {
            // API Error (4xx, 5xx)
            const message = error.response.data?.detail || error.response.data?.message || "Error desconocido";
            console.warn(`API Error [${error.response.status}]: ${message}`);
        }
        return Promise.reject(error);
    }
);

export default apiClient;
