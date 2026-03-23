import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Sgraal Dashboard — Decision Readiness",
  description: "Fleet-wide memory governance dashboard for AI agents.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <nav className="border-b border-surface-light px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <Link href="/" className="font-mono text-gold text-lg font-bold">Sgraal</Link>
            <div className="flex items-center gap-5 text-sm text-muted">
              <Link href="/" className="hover:text-foreground transition">Dashboard</Link>
              <Link href="/verify" className="hover:text-foreground transition">Verify</Link>
            </div>
          </div>
          <span className="text-xs text-muted font-mono">app.sgraal.com</span>
        </nav>
        <main className="flex-1 px-6 py-8 max-w-7xl mx-auto w-full">{children}</main>
      </body>
    </html>
  );
}
