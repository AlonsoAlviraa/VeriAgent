"use client";

import React from "react";
import { useRouter } from "next/navigation";
import {
    CheckCircle2,
    AlertTriangle,
    XCircle,
    ArrowLeft,
    Download,
    ExternalLink,
    ShieldCheck,
    User,
    LogOut
} from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

// Extended history data
const FULL_HISTORY = [
    { id: 1, date: "14 Oct 2023, 10:42", issuer: "Amazon Web Services", logo: "AWS", amount: "45,20 €", status: "FIRMADO", hash: "XJ9K2M..." },
    { id: 2, date: "12 Oct 2023, 16:15", issuer: "Restaurante El Paso", logo: "EP", amount: "120,50 €", status: "REVISAR", hash: "P8Q2L1..." },
    { id: 3, date: "10 Oct 2023, 09:30", issuer: "PC Componentes", logo: "PC", amount: "899,00 €", status: "RECHAZADO", hash: "T5R3K9..." },
    { id: 4, date: "05 Oct 2023, 14:20", issuer: "Telefónica", logo: "TEL", amount: "58,90 €", status: "FIRMADO", hash: "M7V4P2..." },
    { id: 5, date: "01 Oct 2023, 11:00", issuer: "Iberdrola", logo: "IBE", amount: "142,30 €", status: "FIRMADO", hash: "H2N8L5..." },
    { id: 6, date: "28 Sep 2023, 09:15", issuer: "Repsol", logo: "REP", amount: "67,40 €", status: "FIRMADO", hash: "W1Q6R8..." },
    { id: 7, date: "25 Sep 2023, 16:45", issuer: "Endesa", logo: "END", amount: "89,20 €", status: "REVISAR", hash: "U9T5V3..." },
    { id: 8, date: "20 Sep 2023, 10:30", issuer: "Naturgy", logo: "NAT", amount: "76,80 €", status: "FIRMADO", hash: "K4P1M7..." },
];

const StatusBadge = ({ status }: { status: string }) => {
    const styles: Record<string, string> = {
        FIRMADO: "bg-emerald-50 text-emerald-600 border-emerald-100",
        REVISAR: "bg-amber-50 text-amber-600 border-amber-100",
        RECHAZADO: "bg-red-50 text-red-600 border-red-100",
    };

    const styleClass = styles[status] || "bg-slate-50 text-slate-600";

    return (
        <span className={cn("px-2 py-1 rounded-md text-[10px] font-bold border flex items-center gap-1 w-fit", styleClass)}>
            {status === "FIRMADO" && <CheckCircle2 className="w-3 h-3" />}
            {status === "REVISAR" && <AlertTriangle className="w-3 h-3" />}
            {status === "RECHAZADO" && <XCircle className="w-3 h-3" />}
            {status}
        </span>
    );
};

export default function HistoryPage() {
    const router = useRouter();
    const [showProfile, setShowProfile] = React.useState(false);

    const handleDownload = (id: number) => {
        alert(`Descargando factura #${id}`);
    };

    const handleView = (id: number) => {
        alert(`Ver detalles de factura #${id}`);
    };

    return (
        <div className="min-h-screen bg-[#F8FAFC]">
            {/* Top Navigation */}
            <nav className="flex items-center justify-between px-8 py-4 bg-white border-b border-slate-100">
                <div className="flex items-center gap-2">
                    <div className="p-2 bg-emerald-500 rounded-lg text-white">
                        <ShieldCheck className="w-5 h-5" />
                    </div>
                    <span className="font-bold text-slate-800 text-lg">VeriAgent</span>
                </div>
                <div className="flex items-center gap-6">
                    <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-50 text-emerald-600 text-[11px] font-bold border border-emerald-100 uppercase tracking-tight">
                        <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                        Conectado con AEAT
                    </div>
                    <div className="relative">
                        <div
                            onClick={() => setShowProfile(!showProfile)}
                            className="w-10 h-10 rounded-full bg-slate-200 overflow-hidden ring-2 ring-slate-100 cursor-pointer hover:ring-emerald-300 transition-all"
                        >
                            <User className="w-full h-full p-2 text-slate-400" />
                        </div>
                        {showProfile && (
                            <div className="absolute right-0 top-full mt-2 w-48 bg-white rounded-xl shadow-xl border border-slate-100 py-2 z-50">
                                <div className="px-4 py-2 border-b border-slate-50 mb-1">
                                    <p className="text-sm font-bold text-slate-800">Usuario Demo</p>
                                    <p className="text-xs text-slate-500">admin@veriagent.com</p>
                                </div>
                                <button onClick={() => alert('Perfil de usuario')} className="w-full px-4 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-2">
                                    <User className="w-4 h-4" /> Mi Perfil
                                </button>
                                <button onClick={() => router.push('/auth/login')} className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2">
                                    <LogOut className="w-4 h-4" /> Cerrar Sesión
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </nav>

            <main className="max-w-6xl mx-auto px-8 py-10 space-y-8">
                {/* Header with back button */}
                <div className="flex items-center gap-4">
                    <button
                        onClick={() => router.push('/')}
                        className="p-2 hover:bg-slate-100 rounded-lg text-slate-500 transition-colors"
                    >
                        <ArrowLeft className="w-5 h-5" />
                    </button>
                    <div>
                        <h1 className="text-2xl font-black text-slate-900">Historial Completo</h1>
                        <p className="text-slate-500 text-sm">Todas tus facturas procesadas</p>
                    </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-3 gap-4">
                    <div className="bg-white rounded-2xl p-6 border border-slate-100">
                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Total Facturas</p>
                        <p className="text-3xl font-black text-slate-800">{FULL_HISTORY.length}</p>
                    </div>
                    <div className="bg-emerald-50 rounded-2xl p-6 border border-emerald-100">
                        <p className="text-[10px] font-bold text-emerald-600 uppercase tracking-widest mb-2">Firmadas</p>
                        <p className="text-3xl font-black text-emerald-600">{FULL_HISTORY.filter(h => h.status === "FIRMADO").length}</p>
                    </div>
                    <div className="bg-amber-50 rounded-2xl p-6 border border-amber-100">
                        <p className="text-[10px] font-bold text-amber-600 uppercase tracking-widest mb-2">Pendientes</p>
                        <p className="text-3xl font-black text-amber-600">{FULL_HISTORY.filter(h => h.status === "REVISAR").length}</p>
                    </div>
                </div>

                {/* Full History Table */}
                <section className="bg-white rounded-[2rem] p-8 shadow-sm border border-slate-100 overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left">
                            <thead>
                                <tr className="text-[11px] font-black text-slate-400 uppercase tracking-widest border-b border-slate-50">
                                    <th className="pb-4 font-black">Fecha</th>
                                    <th className="pb-4 font-black">Emisor</th>
                                    <th className="pb-4 font-black text-right">Importe</th>
                                    <th className="pb-4 font-black">Hash</th>
                                    <th className="pb-4 font-black pl-8">Estado</th>
                                    <th className="pb-4">Acciones</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-50">
                                {FULL_HISTORY.map((item) => (
                                    <tr key={item.id} className="group hover:bg-slate-50/50 transition-colors">
                                        <td className="py-5 text-sm text-slate-500">{item.date}</td>
                                        <td className="py-5">
                                            <div className="flex items-center gap-3">
                                                <div className="w-10 h-10 rounded-lg bg-slate-900 flex items-center justify-center text-[10px] font-black text-white">
                                                    {item.logo}
                                                </div>
                                                <span className="font-bold text-slate-700 text-sm">{item.issuer}</span>
                                            </div>
                                        </td>
                                        <td className="py-5 text-sm font-black text-slate-800 text-right font-mono">{item.amount}</td>
                                        <td className="py-5 text-xs text-slate-400 font-mono">{item.hash}</td>
                                        <td className="py-5 pl-8">
                                            <StatusBadge status={item.status} />
                                        </td>
                                        <td className="py-5">
                                            <div className="flex items-center gap-2">
                                                <button
                                                    onClick={() => handleView(item.id)}
                                                    className="p-2 hover:bg-slate-100 rounded-lg text-slate-400 hover:text-slate-600"
                                                    title="Ver detalles"
                                                >
                                                    <ExternalLink className="w-4 h-4" />
                                                </button>
                                                <button
                                                    onClick={() => handleDownload(item.id)}
                                                    className="p-2 hover:bg-emerald-50 rounded-lg text-slate-400 hover:text-emerald-600"
                                                    title="Descargar"
                                                >
                                                    <Download className="w-4 h-4" />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </section>
            </main>
        </div>
    );
}
