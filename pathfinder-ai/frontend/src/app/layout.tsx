import type { Metadata, Viewport } from "next";
import { GeistMono } from "geist/font/mono";
import { GeistSans } from "geist/font/sans";
import { Providers } from "@/components/providers";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "PathFinder AI — Your career is a path", template: "%s · PathFinder AI" },
  description:
    "Tell us what you know and what you enjoy. PathFinder AI helps you discover career paths, understand your skill gaps and follow a personalised roadmap.",
};

export const viewport: Viewport = { themeColor: "#fafafa", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable}`}>
      <body className="grain min-h-dvh font-sans">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
