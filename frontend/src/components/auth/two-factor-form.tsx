"use client";

import React, { useState } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { ShieldCheck, Loader2, Fingerprint } from "lucide-react";
import { clsx } from "clsx";

/**
 * [SECURITY-002] Formulario de Segundo Factor (TOTP)
 * Incluye lógica de "Trusted Device" para saltar el login por 30 días.
 */
export default function TwoFactorForm() {
    const [code, setCode] = useState("");
    const [trustDevice, setTrustDevice] = useState(false);
    const [error, setError] = useState("");
    const [isLoading, setIsLoading] = useState(false);

    const { update } = useSession();
    const router = useRouter();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setError("");

        try {
            // 1. Simulación de validación TOTP (En prod llamas a una Server Action o API)
            if (code === "123456") {

                // 2. Si marcó "Confiar", seteamos la cookie (esto lo haría el backend en una llamada real)
                if (trustDevice) {
                    document.cookie = `device_trust_token=valid_for_30_days; Path=/; Max-Age=${30 * 24 * 60 * 60}; SameSite=Strict; Secure`;
                }

                // 3. Actualizamos la sesión JWT para marcar is2FAVerified = true
                await update({ is2FAVerified: true });

                router.push("/dashboard");
            } else {
                setError("Código incorrecto. Inténtalo de nuevo.");
            }
        } catch (err) {
            setError("Error de servidor. Contacta con soporte.");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="w-full max-w-md p-8 bg-white rounded-3xl border border-slate-200 shadow-2xl space-y-8">
            <div className="flex flex-col items-center text-center space-y-2">
                <div className="p-4 rounded-full bg-blue-50 text-blue-600">
                    <ShieldCheck className="w-8 h-8" />
                </div>
                <h2 className="text-2xl font-bold text-slate-800">Verificación 2FA</h2>
                <p className="text-sm text-slate-500">
                    Introduce el código de 6 dígitos de tu aplicación de autenticación.
                </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
                <div className="space-y-2">
                    <label className="text-xs font-bold uppercase tracking-widest text-slate-400">Código TOTP</label>
                    <input
                        type="text"
                        maxLength={6}
                        placeholder="000000"
                        className="w-full text-center text-4xl tracking-[0.5em] font-mono py-4 border-2 border-slate-100 rounded-2xl focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 outline-none transition-all"
                        value={code}
                        onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                        required
                    />
                </div>

                {error && (
                    <div className="p-4 rounded-xl bg-red-50 text-red-600 text-sm font-medium flex items-center gap-2 animate-in fade-in slide-in-from-top-1">
                        <Fingerprint className="w-4 h-4" />
                        {error}
                    </div>
                )}

                {/* [UX-TRUST] Feature: Trusted Device for 30 days */}
                <label className="flex items-center gap-3 p-4 rounded-2xl border border-slate-100 cursor-pointer hover:bg-slate-50 transition-colors">
                    <input
                        type="checkbox"
                        className="w-5 h-5 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                        checked={trustDevice}
                        onChange={(e) => setTrustDevice(e.target.checked)}
                    />
                    <div className="flex flex-col">
                        <span className="text-sm font-bold text-slate-700">Confiar en este dispositivo</span>
                        <span className="text-xs text-slate-400">No pedir códigos en este navegador por 30 días.</span>
                    </div>
                </label>

                <button
                    type="submit"
                    disabled={code.length !== 6 || isLoading}
                    className="w-full flex items-center justify-center gap-2 py-4 bg-slate-900 text-white font-bold rounded-2xl hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-xl shadow-slate-900/20"
                >
                    {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : "Verificar y Acceder"}
                </button>
            </form>
        </div>
    );
}
