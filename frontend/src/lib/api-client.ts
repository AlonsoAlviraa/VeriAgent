import axios from "axios";

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

const apiClient = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
    headers: {
        "Content-Type": "application/json",
    },
});

// Request Interceptor: inyecta X-Tenant-Id en cada llamada (PUX-05).
apiClient.interceptors.request.use((config) => {
    const tenantId = getActiveTenant();
    if (tenantId) {
        config.headers = config.headers ?? {};
        config.headers["X-Tenant-Id"] = tenantId;
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
