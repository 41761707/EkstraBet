import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { cookies } from "next/headers";

import { AppHeader } from "@/components/AppHeader";
import { PreferencesProvider } from "@/components/preferences/PreferencesProvider";
import { ThemeBootstrapScript } from "@/components/preferences/ThemeBootstrapScript";
import { getAuthCookieName, isAuthEnabled } from "@/lib/authCookie";
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

  const jar = await cookies();
  const hasSession =
    isAuthEnabled() && Boolean(jar.get(getAuthCookieName())?.value);

  return (
    <html lang="pl" suppressHydrationWarning>
      <head>
        <ThemeBootstrapScript />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} min-h-screen antialiased`}
      >
        <PreferencesProvider hasSession={hasSession}>
          <AppHeader />
          <main className="mx-auto min-w-0 max-w-6xl overflow-x-hidden px-4 py-8">
            {children}
          </main>
        </PreferencesProvider>
      </body>
    </html>
  );
}
