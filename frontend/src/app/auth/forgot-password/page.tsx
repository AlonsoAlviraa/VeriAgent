"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Mail, ShieldCheck, ArrowRight, KeyRound } from "lucide-react";

export default function ForgotPasswordPage() {
    const [email, setEmail] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const router = useRouter();

    const handleResetRequest = (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        // Simulación de envío de código de recuperación
        setTimeout(() => {
            setIsLoading(false);
            router.push("/auth/verify-recovery");
        }, 1500);
    };

    return (
        <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6 selection:bg-blue-100 selection:text-blue-900">
            <div className="w-full max-w-md space-y-8 bg-white p-10 rounded-[2.5rem] border border-slate-100 shadow-2xl">
                <div className="text-center space-y-3">
                    <div className="inline-flex p-4 rounded-3xl bg-amber-50 text-amber-600 mb-2">
                        <KeyRound className="w-8 h-8" />
                    </div>
                    <h1 className="text-3xl font-black text-slate-800 tracking-tight">Recuperar Acceso</h1>
                    <p className="text-slate-500 text-sm font-medium">Enviaremos un código TOTP a tu email</p>
                </div>

                <form onSubmit={handleResetRequest} className="space-y-6">
                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 pl-1">Email Corporativo</label>
                        <div className="relative">
                            <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-300" />
                            <input
                                type="email"
                                placeholder="juan@empresa.com"
                                className="w-full pl-12 pr-4 py-4 bg-slate-50 border border-slate-100 rounded-2xl focus:border-blue-500 focus:ring-4 focus:ring-blue-500/5 outline-none transition-all placeholder:text-slate-300"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                            />
                        </div>
                    </div>

                    <button
                        type="submit"
                        disabled={isLoading}
                        className="w-full flex items-center justify-center gap-2 group py-4 bg-slate-900 text-white font-black rounded-2xl hover:bg-slate-800 transition-all shadow-xl shadow-slate-900/10 disabled:opacity-50"
                    >
                        {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <>Continuar <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" /></>}
                    </button>
                </form>

                <div className="text-center pt-2">
                    <Link href="/auth/login" className="text-sm text-slate-400 font-medium hover:text-slate-600 transition-colors">
                        ← Volver al inicio de sesión
                    </Link>
                </div>
            </div>
        </div>
    );
}

const Loader2 = ({ className }: { className?: string }) => (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12a9 9 0 1 1-6.219-8.56" /></svg>
);
