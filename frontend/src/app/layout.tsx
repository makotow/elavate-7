import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HR Agentic Solution (MVP 1) | Google ADK & Vertex AI",
  description: "Enterprise HR Agentic Assistant powered by Google Agent Development Kit 2.8 & Gemini Enterprise Agent Platform",
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
