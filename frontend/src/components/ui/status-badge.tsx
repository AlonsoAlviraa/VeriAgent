"use client";

import React from "react";
import { CheckCircle2, XCircle, Clock, AlertTriangle, FileCheck, Loader2 } from "lucide-react";
import { InvoiceStatus } from "@/lib/types/api";

interface StatusBadgeProps {
    status: InvoiceStatus | string;
    size?: "sm" | "md" | "lg";
}

const statusConfig: Record<string, {
    label: string;
    bgColor: string;
    textColor: string;
    borderColor: string;
    icon: React.ReactNode;
    tooltip?: string;
}> = {
    [InvoiceStatus.SENT_OK]: {
        label: "ENVIADA AEAT",
        bgColor: "bg-[#eef8f1]",
        textColor: "text-[#17663f]",
        borderColor: "border-[#c8e6d3]",
        icon: <CheckCircle2 className="w-3.5 h-3.5" />,
        tooltip: "Factura aceptada por Hacienda",
    },
    [InvoiceStatus.REJECTED_AEAT]: {
        label: "RECHAZADA",
        bgColor: "bg-[#fbefee]",
        textColor: "text-[#9b2c2c]",
        borderColor: "border-[#f0c7c3]",
        icon: <XCircle className="w-3.5 h-3.5" />,
        tooltip: "Ver error en logs",
    },
    [InvoiceStatus.SIGNED]: {
        label: "PENDIENTE ENVIO",
        bgColor: "bg-[#fbf3e8]",
        textColor: "text-[#9a4d09]",
        borderColor: "border-[#f3d5b0]",
        icon: <Clock className="w-3.5 h-3.5" />,
        tooltip: "Firmada, pendiente de envio a AEAT",
    },
    [InvoiceStatus.VALIDATED]: {
        label: "VALIDADA",
        bgColor: "bg-[#eef4fb]",
        textColor: "text-[#185fa5]",
        borderColor: "border-[#c9d9ee]",
        icon: <FileCheck className="w-3.5 h-3.5" />,
    },
    [InvoiceStatus.PROCESSING]: {
        label: "PROCESANDO",
        bgColor: "bg-[#f4f3f0]",
        textColor: "text-[#6f6e69]",
        borderColor: "border-[#e8e6e3]",
        icon: <Loader2 className="w-3.5 h-3.5 animate-spin" />,
    },
    [InvoiceStatus.DRAFT]: {
        label: "BORRADOR",
        bgColor: "bg-[#f4f3f0]",
        textColor: "text-[#6f6e69]",
        borderColor: "border-[#e8e6e3]",
        icon: <Clock className="w-3.5 h-3.5" />,
    },
    [InvoiceStatus.ERROR]: {
        label: "ERROR",
        bgColor: "bg-[#fbefee]",
        textColor: "text-[#9b2c2c]",
        borderColor: "border-[#f0c7c3]",
        icon: <AlertTriangle className="w-3.5 h-3.5" />,
    },
};

// Fallback for legacy statuses
const legacyStatusMap: Record<string, string> = {
    "FIRMADO": InvoiceStatus.SENT_OK,
    "REVISAR": InvoiceStatus.SIGNED,
    "RECHAZADO": InvoiceStatus.REJECTED_AEAT,
    "PENDING": InvoiceStatus.PROCESSING,
    "SENT": InvoiceStatus.SENT_OK,
};

export function StatusBadge({ status, size = "sm" }: StatusBadgeProps) {
    // Map legacy status if needed
    const mappedStatus = legacyStatusMap[status] || status;
    const config = statusConfig[mappedStatus] || statusConfig[InvoiceStatus.DRAFT];

    const sizeClasses = {
        sm: "px-2 py-1 text-[10px]",
        md: "px-3 py-1.5 text-xs",
        lg: "px-4 py-2 text-sm",
    };

    return (
        <span
            className={`
        inline-flex items-center gap-1.5 font-medium rounded-full border
        ${config.bgColor} ${config.textColor} ${config.borderColor}
        ${sizeClasses[size]}
      `}
            title={config.tooltip}
        >
            {config.icon}
            {config.label}
        </span>
    );
}

export default StatusBadge;
