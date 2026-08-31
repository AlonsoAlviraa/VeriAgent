import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Security",
  description:
    "The LLM never writes the hash. Model Armor, tenant isolation, fail-closed AEAT production.",
};

export default function SecurityLayout({ children }: { children: React.ReactNode }) {
  return children;
}
