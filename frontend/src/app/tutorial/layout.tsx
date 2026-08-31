import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Tutorial",
  description:
    "Operator guide for AEAT electronic certificates. Fleet ingest signs locally and does not call AEAT.",
};

export default function TutorialLayout({ children }: { children: React.ReactNode }) {
  return children;
}
