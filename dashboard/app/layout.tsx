import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { NavBar } from "./components/NavBar";
import { ClientShell } from "./components/ClientShell";
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
        <ClientShell>
          <NavBar />
          <main className="flex-1 px-6 py-8 max-w-7xl mx-auto w-full">{children}</main>
        </ClientShell>
      </body>
    </html>
  );
}
