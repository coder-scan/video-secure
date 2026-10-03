import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Secure Video Platform - Studio",
  description: "Secure Video Hosting, Anti-Piracy Infrastructure & Leak Intelligence",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950 text-slate-100 antialiased selection:bg-indigo-500 selection:text-white">
        {children}
      </body>
    </html>
  );
}
