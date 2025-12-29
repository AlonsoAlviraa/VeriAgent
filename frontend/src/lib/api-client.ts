import axios from "axios";

/**
 * [FE-002] Configured Axios instance for VeriAgent Backend.
 * Handles base URL and generic network errors.
 */
const apiClient = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
    headers: {
        "Content-Type": "application/json",
    },
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
