"use client";

import React from "react";
import Link from "next/link";
import { User, Mail, Lock, ShieldCheck, ArrowRight } from "lucide-react";

export default function RegisterPage() {
    const [formData, setFormData] = React.useState({
        name: "",
        email: "",
        password: "",
    });

    const handleRegister = (e: React.FormEvent) => {
        e.preventDefault();
        console.log("Registering...", formData);
    };

    return (
        <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6 selection:bg-blue-100 selection:text-blue-900">
            <div className="w-full max-w-md space-y-8 bg-white p-10 rounded-[2.5rem] border border-slate-100 shadow-2xl">
                <div className="text-center space-y-3">
                    <div className="inline-flex p-4 rounded-3xl bg-blue-50 text-blue-600 mb-2">
                        <ShieldCheck className="w-8 h-8" />
                    </div>
                    <h1 className="text-3xl font-black text-slate-800 tracking-tight">Crea tu cuenta</h1>
                    <p className="text-slate-500 text-sm font-medium">Únete a la nueva era de cumplimiento fiscal</p>
                </div>

                <form onSubmit={handleRegister} className="space-y-5">
                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 pl-1">Nombre Completo</label>
                        <div className="relative">
                            <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-300" />
                            <input
                                type="text"
                                placeholder="Juan Pérez"
                                className="w-full pl-12 pr-4 py-4 bg-slate-50 border border-slate-100 rounded-2xl focus:border-blue-500 focus:ring-4 focus:ring-blue-500/5 outline-none transition-all placeholder:text-slate-300"
                                value={formData.name}
                                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                required
                            />
                        </div>
                    </div>

                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 pl-1">Email Corporativo</label>
                        <div className="relative">
                            <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-300" />
                            <input
                                type="email"
                                placeholder="juan@empresa.com"
                                className="w-full pl-12 pr-4 py-4 bg-slate-50 border border-slate-100 rounded-2xl focus:border-blue-500 focus:ring-4 focus:ring-blue-500/5 outline-none transition-all placeholder:text-slate-300"
                                value={formData.email}
                                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                required
                            />
                        </div>
                    </div>

                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 pl-1">Contraseña</label>
                        <div className="relative">
                            <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-300" />
                            <input
                                type="password"
                                placeholder="••••••••"
                                className="w-full pl-12 pr-4 py-4 bg-slate-50 border border-slate-100 rounded-2xl focus:border-blue-500 focus:ring-4 focus:ring-blue-500/5 outline-none transition-all placeholder:text-slate-300"
                                value={formData.password}
                                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                required
                            />
                        </div>
                    </div>

                    <button
                        type="submit"
                        className="w-full flex items-center justify-center gap-2 group py-4 bg-slate-900 text-white font-black rounded-2xl hover:bg-slate-800 transition-all shadow-xl shadow-slate-900/10"
                    >
                        Registrarme <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                    </button>
                </form>

                <div className="text-center pt-2">
                    <p className="text-sm text-slate-400 font-medium">
                        ¿Ya tienes cuenta? {" "}
                        <Link href="/auth/login" className="text-blue-600 font-black hover:underline underline-offset-4">
                            Inicia sesión
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    );
}
