"use client";

import React, { useState } from "react";
import { Download, Printer, ShieldAlert, Check } from "lucide-react";

/**
 * [SECURITY-003] Códigos de Recuperación del 2FA (Plan B)
 */
export default function BackupCodesScreen() {
    const [codes] = useState([
        "AV23-X982-11PQ", "L092-ZS12-9902", "MK01-PP22-ZX88", "QQ99-1200-LL72",
        "BB11-9988-MM33", "ZZ00-1122-3344", "FF55-XX66-YY77", "HH88-KK99-JJ00"
    ]);
    const [copied, setCopied] = useState(false);

    const copyToClipboard = () => {
        navigator.clipboard.writeText(codes.join("\n"));
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="w-full max-w-2xl mx-auto p-12 bg-white rounded-3xl border border-slate-200 shadow-xl space-y-10 mt-12">
            <div className="space-y-4">
                <div className="inline-flex p-3 rounded-2xl bg-amber-50 text-amber-600">
                    <ShieldAlert className="w-8 h-8" />
                </div>
                <h1 className="text-3xl font-black text-slate-800">Códigos de Recuperación</h1>
                <p className="text-slate-500 leading-relaxed">
                    Guarda estos códigos en un lugar seguro (y fuera de tu móvil). Si pierdes el acceso a tu aplicación de autenticación,
                    estos códigos serán la <strong>única forma</strong> de recuperar tu cuenta bancaria y fiscal en VeriAgent.
                </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
                {codes.map((code) => (
                    <div key={code} className="p-4 bg-slate-50 border border-slate-100 rounded-xl text-center font-mono font-bold text-slate-600 tracking-wider">
                        {code}
                    </div>
                ))}
            </div>

            <div className="pt-6 flex flex-col sm:flex-row gap-4">
                <button
                    onClick={copyToClipboard}
                    className="flex-1 flex items-center justify-center gap-2 py-4 bg-slate-900 text-white font-bold rounded-2xl hover:bg-slate-800 transition-all"
                >
                    {copied ? <Check className="w-5 h-5" /> : <Download className="w-5 h-5" />}
                    {copied ? "¡Copiado!" : "Copiar Códigos"}
                </button>
                <button
                    onClick={() => window.print()}
                    className="flex-1 flex items-center justify-center gap-2 py-4 bg-white border border-slate-200 text-slate-600 font-bold rounded-2xl hover:bg-slate-50 transition-all"
                >
                    <Printer className="w-5 h-5" />
                    Imprimir / Guardar PDF
                </button>
            </div>

            <div className="p-6 rounded-2xl bg-amber-50 border border-amber-100">
                <p className="text-xs font-bold text-amber-800 uppercase tracking-widest mb-1">Nota Crítica:</p>
                <p className="text-xs text-amber-700">
                    Cada código solo puede ser usado una vez. Una vez agotados, deberás generar un nuevo set en la configuración de seguridad.
                </p>
            </div>
        </div>
    );
}
