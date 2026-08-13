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
        bgColor: "bg-emerald-400/12",
        textColor: "text-emerald-300",
        borderColor: "border-emerald-400/25",
        icon: <CheckCircle2 className="w-3.5 h-3.5" />,
        tooltip: "Factura aceptada por Hacienda",
    },
    [InvoiceStatus.REJECTED_AEAT]: {
        label: "RECHAZADA",
        bgColor: "bg-rose-400/12",
        textColor: "text-rose-300",
        borderColor: "border-rose-400/25",
        icon: <XCircle className="w-3.5 h-3.5" />,
        tooltip: "Ver error en logs",
    },
    [InvoiceStatus.SIGNED]: {
        label: "PENDIENTE ENVIO",
        bgColor: "bg-amber-400/12",
        textColor: "text-amber-200",
        borderColor: "border-amber-400/25",
        icon: <Clock className="w-3.5 h-3.5" />,
        tooltip: "Firmada, pendiente de envio a AEAT",
    },
    [InvoiceStatus.VALIDATED]: {
        label: "VALIDADA",
        bgColor: "bg-sky-400/12",
        textColor: "text-sky-300",
        borderColor: "border-sky-400/25",
        icon: <FileCheck className="w-3.5 h-3.5" />,
    },
    [InvoiceStatus.PROCESSING]: {
        label: "PROCESANDO",
        bgColor: "bg-white/6",
        textColor: "text-slate-300",
        borderColor: "border-white/10",
        icon: <Loader2 className="w-3.5 h-3.5 animate-spin" />,
    },
    [InvoiceStatus.DRAFT]: {
        label: "BORRADOR",
        bgColor: "bg-white/6",
        textColor: "text-slate-400",
        borderColor: "border-white/10",
        icon: <Clock className="w-3.5 h-3.5" />,
    },
    [InvoiceStatus.ERROR]: {
        label: "ERROR",
        bgColor: "bg-rose-400/12",
        textColor: "text-rose-300",
        borderColor: "border-rose-400/25",
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
        inline-flex items-center gap-1.5 font-bold rounded-lg border
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
