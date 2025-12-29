"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { ShieldCheck, Loader2, Fingerprint, ArrowRight } from "lucide-react";
import { clsx } from "clsx";

/**
 * [SECURITY-004] Verificación TOTP para Recuperación de Contraseña
 */
export default function VerifyRecoveryPage() {
    const [code, setCode] = useState("");
    const [error, setError] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const router = useRouter();

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setError("");

        // Validación simulada
        setTimeout(() => {
            if (code === "123456") {
                router.push("/auth/reset-password");
            } else {
                setError("Código de recuperación incorrecto.");
                setIsLoading(false);
            }
        }, 1500);
    };

    return (
        <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6 selection:bg-blue-100 selection:text-blue-900">
            <div className="w-full max-w-md space-y-8 bg-white p-10 rounded-[2.5rem] border border-slate-100 shadow-2xl">
                <div className="flex flex-col items-center text-center space-y-3">
                    <div className="p-4 rounded-3xl bg-blue-50 text-blue-600 mb-2">
                        <ShieldCheck className="w-8 h-8" />
                    </div>
                    <h2 className="text-3xl font-black text-slate-800 tracking-tight">Verifica tu Identidad</h2>
                    <p className="text-sm text-slate-500 font-medium leading-relaxed">
                        Hemos enviado un código a tu email. Introdúcelo para continuar con la recuperación.
                    </p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-8">
                    <div className="space-y-3">
                        <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 text-center block">Código de 6 dígitos</label>
                        <input
                            type="text"
                            maxLength={6}
                            placeholder="000000"
                            className="w-full text-center text-4xl tracking-[0.5em] font-mono py-5 bg-slate-50 border border-slate-100 rounded-2xl focus:border-blue-500 focus:ring-4 focus:ring-blue-500/5 outline-none transition-all placeholder:text-slate-200"
                            value={code}
                            onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                            required
                        />
                    </div>

                    {error && (
                        <div className="p-4 rounded-xl bg-red-50 text-red-600 text-xs font-bold flex items-center gap-2 animate-in fade-in slide-in-from-top-1">
                            <Fingerprint className="w-4 h-4" />
                            {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={code.length !== 6 || isLoading}
                        className="w-full flex items-center justify-center gap-2 py-4 bg-slate-900 text-white font-black rounded-2xl hover:bg-slate-800 disabled:opacity-50 transition-all shadow-xl shadow-slate-900/10"
                    >
                        {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <>Validar y Continuar <ArrowRight className="w-4 h-4" /></>}
                    </button>
                </form>

                <div className="text-center">
                    <button className="text-xs font-bold text-slate-400 hover:text-blue-600 transition-colors">
                        ¿No recibiste el código? Reenviar
                    </button>
                </div>
            </div>
        </div>
    );
}
