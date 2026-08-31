import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Pricing",
  description: "Contest-honest monthly plans. Demo is free. AEAT remittance is not included live.",
};

export default function PricingLayout({ children }: { children: React.ReactNode }) {
  return children;
}
