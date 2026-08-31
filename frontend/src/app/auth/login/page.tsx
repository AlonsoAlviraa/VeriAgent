"use client";

import React from "react";
import { signIn } from "next-auth/react";
import { Mail, ShieldCheck, Lock } from "lucide-react";

import Link from "next/link";
import { LocaleToggle } from "@/components/i18n/locale-toggle";
import { useLocale } from "@/components/i18n/locale-provider";

export default function LoginPage() {
    const { t } = useLocale();
    const [formData, setFormData] = React.useState({
        email: "",
        password: "",
    });

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        await signIn("credentials", {
            email: formData.email,
            password: formData.password,
            callbackUrl: "/dashboard"
        });
    };

    return (
        <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6 selection:bg-blue-100 selection:text-blue-900">
            <div className="absolute right-4 top-4">
                <LocaleToggle />
            </div>
            <div className="w-full max-w-md space-y-8 bg-white p-10 rounded-[2.5rem] border border-slate-100 shadow-2xl">
                <div className="text-center space-y-3">
                    <div className="inline-flex p-4 rounded-3xl bg-blue-50 text-blue-600 mb-2">
                        <ShieldCheck className="w-8 h-8" />
                    </div>
                    <h1 className="text-3xl font-black text-slate-800 tracking-tight">{t("login.title")}</h1>
                    <p className="text-slate-500 text-sm font-medium">{t("login.subtitle")}</p>
                </div>

                <form onSubmit={handleLogin} className="space-y-6">
                    <div className="space-y-4">
                        <div className="space-y-1.5">
                            <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 pl-1">{t("login.email")}</label>
                            <div className="relative">
                                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-300" />
                                <input
                                    type="email"
                                    placeholder="alonsotest@veriagent.com"
                                    className="w-full pl-12 pr-4 py-4 bg-slate-50 border border-slate-100 rounded-2xl focus:border-blue-500 focus:ring-4 focus:ring-blue-500/5 outline-none transition-all placeholder:text-slate-300"
                                    value={formData.email}
                                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                    required
                                />
                            </div>
                        </div>

                        <div className="space-y-1.5">
                            <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 pl-1">{t("login.password")}</label>
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
                            <div className="text-right pr-2">
                                <Link href="/auth/forgot-password" className="text-[11px] font-bold text-blue-500 hover:underline">
                                    {t("login.forgot")}
                                </Link>
                            </div>
                        </div>
                    </div>

                    <button
                        type="submit"
                        className="w-full py-4 bg-slate-900 text-white font-black rounded-2xl hover:bg-slate-800 transition-all shadow-xl shadow-slate-900/10"
                    >
                        {t("login.submit")}
                    </button>
                </form>

                <div className="text-center pt-2">
                    <p className="text-sm text-slate-400 font-medium">
                        {t("login.noAccount")}{" "}
                        <Link href="/auth/register" className="text-blue-600 font-black hover:underline underline-offset-4">
                            {t("login.register")}
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    );
}
