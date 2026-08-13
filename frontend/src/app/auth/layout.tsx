"use client";

import type { ReactNode } from "react";
import { SessionProvider } from "next-auth/react";

/** next-auth SessionProvider is auth-only — keep it off the /fleet client graph. */
export default function AuthLayout({ children }: { children: ReactNode }) {
  return <SessionProvider>{children}</SessionProvider>;
}
