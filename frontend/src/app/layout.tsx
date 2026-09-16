import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Elevate Workplace Portal | Google ADK 2.9 & Gemini 3.8 Flash",
  description: "Enterprise HR & IT Agentic Concierge powered by Google Agent Development Kit 2.9, Gemini 3.8 Flash & FastMCP",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja">
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased">
        {children}
      </body>
    </html>
  );
}
