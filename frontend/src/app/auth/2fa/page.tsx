"use client";

import React from "react";
import TwoFactorForm from "@/components/auth/two-factor-form";

export default function TwoFactorPage() {
    return (
        <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6">
            <div className="w-full max-w-md">
                <TwoFactorForm />
            </div>
        </div>
    );
}
