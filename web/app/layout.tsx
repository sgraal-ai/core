import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Sgraal — Memory Governance for AI Agents",
  description:
    "Before your AI agent acts, Sgraal checks if its memory is still true. One preflight call. Under 10ms. 9 risk components. Full explainability.",
  metadataBase: new URL("https://sgraal.com"),
  openGraph: {
    title: "Sgraal — Memory Governance for AI Agents",
    description:
      "Your AI agent doesn't know it's forgetting. Sgraal catches stale, conflicting, and drifted memory before your agent acts.",
    url: "https://sgraal.com",
    siteName: "Sgraal",
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "Sgraal — Memory Governance for AI Agents",
    description:
      "Your AI agent doesn't know it's forgetting. Sgraal catches it in under 10ms.",
  },
  robots: {
    index: true,
    follow: true,
  },
  alternates: {
    canonical: "https://sgraal.com",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
