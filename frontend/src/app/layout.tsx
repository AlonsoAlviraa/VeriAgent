import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import QueryProvider from "@/components/providers/query-provider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "VeriFleet — Fortified Enterprise Fleet",
    template: "%s · VeriFleet",
  },
  description:
    "Autonomous fiscal-compliance fleet for Spanish VeriFactu. Gemini 3.5 + Google ADK. The LLM never writes the hash.",
  icons: { icon: "/favicon.ico" },
};

export const viewport: Viewport = {
  colorScheme: "light",
  themeColor: "#fbfbf9",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="light" style={{ colorScheme: "only light" }}>
      <head>
        <meta name="color-scheme" content="only light" />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
        style={{ backgroundColor: "#fbfbf9", color: "#111111" }}
      >
        <QueryProvider>
          {children}
        </QueryProvider>
      </body>
    </html>
  );
}

