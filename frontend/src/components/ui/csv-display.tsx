"use client";

import React, { useState } from "react";
import { Copy, Check, ShieldCheck } from "lucide-react";

interface CSVDisplayProps {
    csv: string;
    compact?: boolean;
}

export function CSVDisplay({ csv, compact = false }: CSVDisplayProps) {
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
        await navigator.clipboard.writeText(csv);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    if (compact) {
        return (
            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-emerald-50 border border-emerald-100 rounded-lg">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <code className="font-mono text-xs font-bold text-emerald-700">{csv}</code>
                <button
                    onClick={handleCopy}
                    className="p-1 hover:bg-emerald-100 rounded transition-colors"
                    title="Copiar CSV"
                >
                    {copied ? (
                        <Check className="w-3.5 h-3.5 text-emerald-600" />
                    ) : (
                        <Copy className="w-3.5 h-3.5 text-emerald-500" />
                    )}
                </button>
            </div>
        );
    }

    return (
        <div className="bg-emerald-50/50 border border-emerald-100 rounded-2xl p-4 space-y-2">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <ShieldCheck className="w-5 h-5 text-emerald-600" />
                    <span className="text-[10px] font-black uppercase tracking-widest text-emerald-800">
                        Codigo Seguro de Verificacion (CSV)
                    </span>
                </div>
                <button
                    onClick={handleCopy}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-100 hover:bg-emerald-200 rounded-lg transition-colors text-emerald-700 text-xs font-bold"
                >
                    {copied ? (
                        <>
                            <Check className="w-4 h-4" /> Copiado
                        </>
                    ) : (
                        <>
                            <Copy className="w-4 h-4" /> Copiar
                        </>
                    )}
                </button>
            </div>
            <div className="flex items-center gap-3 bg-white border border-emerald-100 rounded-xl px-4 py-3">
                <code className="font-mono text-lg font-black text-emerald-700 tracking-wider flex-1">
                    {csv}
                </code>
            </div>
            <p className="text-[10px] text-emerald-600 font-medium">
                Este codigo acredita que Hacienda ha recibido y validado la factura.
            </p>
        </div>
    );
}

export default CSVDisplay;
