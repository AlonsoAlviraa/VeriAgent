"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { Lock, ShieldCheck, CheckCircle2, Loader2, ArrowRight } from "lucide-react";

export default function ResetPasswordPage() {
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [isSuccess, setIsSuccess] = useState(false);
    const router = useRouter();

    const handleReset = (e: React.FormEvent) => {
        e.preventDefault();
        if (password !== confirmPassword) return;

        setIsLoading(true);
        // Simulación de cambio de contraseña
        setTimeout(() => {
            setIsLoading(false);
            setIsSuccess(true);
            setTimeout(() => router.push("/auth/login"), 3000);
        }, 2000);
    };

    if (isSuccess) {
        return (
            <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6">
                <div className="w-full max-w-md bg-white p-12 rounded-[2.5rem] border border-slate-100 shadow-2xl text-center space-y-6">
                    <div className="inline-flex p-5 rounded-full bg-emerald-50 text-emerald-600 animate-bounce">
                        <CheckCircle2 className="w-12 h-12" />
                    </div>
                    <h2 className="text-3xl font-black text-slate-800">¡Contraseña Cambiada!</h2>
                    <p className="text-slate-500 font-medium leading-relaxed">
                        Tu acceso ha sido restaurado. Redirigiendo al inicio de sesión en unos segundos...
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6 selection:bg-blue-100 selection:text-blue-900">
            <div className="w-full max-w-md space-y-8 bg-white p-10 rounded-[2.5rem] border border-slate-100 shadow-2xl">
                <div className="text-center space-y-3">
                    <div className="inline-flex p-4 rounded-3xl bg-blue-50 text-blue-600 mb-2">
                        <Lock className="w-8 h-8" />
                    </div>
                    <h1 className="text-3xl font-black text-slate-800 tracking-tight">Nueva Contraseña</h1>
                    <p className="text-slate-500 text-sm font-medium">Define una contraseña robusta para proteger tus activos</p>
                </div>

                <form onSubmit={handleReset} className="space-y-5">
                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 pl-1">Nueva Contraseña</label>
                        <div className="relative">
                            <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-300" />
                            <input
                                type="password"
                                placeholder="••••••••"
                                className="w-full pl-12 pr-4 py-4 bg-slate-50 border border-slate-100 rounded-2xl focus:border-blue-500 focus:ring-4 focus:ring-blue-500/5 outline-none transition-all placeholder:text-slate-300"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                            />
                        </div>
                    </div>

                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 pl-1">Confirmar Contraseña</label>
                        <div className="relative">
                            <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-300" />
                            <input
                                type="password"
                                placeholder="••••••••"
                                className="w-full pl-12 pr-4 py-4 bg-slate-50 border border-slate-100 rounded-2xl focus:border-blue-500 focus:ring-4 focus:ring-blue-500/5 outline-none transition-all placeholder:text-slate-300"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                required
                            />
                        </div>
                        {password !== confirmPassword && confirmPassword !== "" && (
                            <p className="text-[10px] text-red-500 font-bold mt-1 ml-1 px-2">Las contraseñas no coinciden</p>
                        )}
                    </div>

                    <button
                        type="submit"
                        disabled={isLoading || password !== confirmPassword || password === ""}
                        className="w-full flex items-center justify-center gap-2 group py-4 bg-slate-900 text-white font-black rounded-2xl hover:bg-slate-800 transition-all shadow-xl shadow-slate-900/10 disabled:opacity-50"
                    >
                        {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <>Cambiar Contraseña <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" /></>}
                    </button>
                </form>
            </div>
        </div>
    );
}
