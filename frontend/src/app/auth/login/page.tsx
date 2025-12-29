"use client";

import React from "react";
import { signIn } from "next-auth/react";
import { Mail, ShieldCheck, Lock } from "lucide-react"; // Added Lock import

import Link from "next/link";

export default function LoginPage() {
    const [formData, setFormData] = React.useState({
        email: "",
        password: "",
    });

    const handleLogin = async (e: React.FormEvent) => { // Made handleLogin async
        e.preventDefault();
        // Use 'credentials' provider instead of 'resend'
        await signIn("credentials", {
            email: formData.email,
            password: formData.password,
            callbackUrl: "/dashboard" // Changed callbackUrl
        });
    };

    return (
        <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6 selection:bg-blue-100 selection:text-blue-900">
            <div className="w-full max-w-md space-y-8 bg-white p-10 rounded-[2.5rem] border border-slate-100 shadow-2xl">
                <div className="text-center space-y-3">
                    <div className="inline-flex p-4 rounded-3xl bg-blue-50 text-blue-600 mb-2">
                        <ShieldCheck className="w-8 h-8" />
                    </div>
                    <h1 className="text-3xl font-black text-slate-800 tracking-tight">VeriAgent Login</h1>
                    <p className="text-slate-500 text-sm font-medium">Acceso seguro para Auditoría Fiscal</p>
                </div>

                <form onSubmit={handleLogin} className="space-y-6">
                    <div className="space-y-4"> {/* Changed to space-y-4 */}
                        <div className="space-y-1.5"> {/* New div for email field */}
                            <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 pl-1">Email Corporativo</label>
                            <div className="relative">
                                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-300" />
                                <input
                                    type="email"
                                    placeholder="alonsotest@veriagent.com" // Updated placeholder
                                    className="w-full pl-12 pr-4 py-4 bg-slate-50 border border-slate-100 rounded-2xl focus:border-blue-500 focus:ring-4 focus:ring-blue-500/5 outline-none transition-all placeholder:text-slate-300"
                                    value={formData.email} // Updated value
                                    onChange={(e) => setFormData({ ...formData, email: e.target.value })} // Updated onChange
                                    required
                                />
                            </div>
                        </div>

                        <div className="space-y-1.5"> {/* New div for password field */}
                            <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 pl-1">Contraseña</label>
                            <div className="relative">
                                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-300" /> {/* Added Lock icon */}
                                <input
                                    type="password"
                                    placeholder="••••••••"
                                    className="w-full pl-12 pr-4 py-4 bg-slate-50 border border-slate-100 rounded-2xl focus:border-blue-500 focus:ring-4 focus:ring-blue-500/5 outline-none transition-all placeholder:text-slate-300"
                                    value={formData.password} // New password state
                                    onChange={(e) => setFormData({ ...formData, password: e.target.value })} // New password onChange
                                    required
                                />
                            </div>
                            <div className="text-right pr-2">
                                {/* Removed the hidden link */}
                                <Link href="/auth/forgot-password" className="text-[11px] font-bold text-blue-500 hover:underline"> {/* Updated link classes */}
                                    Olvidé mi contraseña
                                </Link>
                            </div>
                        </div>
                    </div>

                    <button
                        type="submit"
                        className="w-full py-4 bg-slate-900 text-white font-black rounded-2xl hover:bg-slate-800 transition-all shadow-xl shadow-slate-900/10"
                    >
                        Enviar Enlace de Acceso
                    </button>
                </form>

                <div className="text-center pt-2">
                    <p className="text-sm text-slate-400 font-medium">
                        ¿No tienes cuenta? {" "}
                        <Link href="/auth/register" className="text-blue-600 font-black hover:underline underline-offset-4">
                            Regístrate
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    );
}
