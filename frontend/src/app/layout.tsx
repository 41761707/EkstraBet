import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { AppHeader } from "@/components/AppHeader";
import { ThemeBootstrapScript } from "@/components/preferences/ThemeBootstrapScript";
import { redirectIfFirstLoginIncomplete } from "@/lib/firstLoginGate";
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
  title: "EkstraBet",
  description: "Asystent analityki sportowej",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  await redirectIfFirstLoginIncomplete();

  return (
    <html lang="pl" suppressHydrationWarning>
      <head>
        <ThemeBootstrapScript />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} min-h-screen antialiased`}
      >
        <AppHeader />
        <main className="mx-auto min-w-0 max-w-6xl overflow-x-hidden px-4 py-8">
          {children}
        </main>
      </body>
    </html>
  );
}
