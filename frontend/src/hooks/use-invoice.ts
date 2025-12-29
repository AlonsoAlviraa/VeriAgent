import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api-client";
import { InvoiceOutput, InvoiceStatus } from "@/lib/types/api";

/**
 * [FE-003] Hook to poll invoice status from the backend.
 * Automatically stops polling when the status reaches a terminal state (SIGNED or ERROR).
 */
export const useInvoiceStatus = (invoiceId: string | null) => {
    return useQuery({
        queryKey: ["invoice", invoiceId],
        queryFn: async () => {
            const response = await apiClient.get<InvoiceOutput>(`/api/v1/invoices/${invoiceId}`);
            return response.data;
        },
        enabled: !!invoiceId,
        refetchInterval: (query) => {
            const status = query.state.data?.status;
            if (status === InvoiceStatus.SIGNED || status === InvoiceStatus.ERROR) {
                return false;
            }
            return 3000; // Poll every 3 seconds
        },
    });
};
