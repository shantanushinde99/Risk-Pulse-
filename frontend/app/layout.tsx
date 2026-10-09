import type { Metadata } from "next";
import { Space_Grotesk, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import Shell from "./shell";

const grotesk = Space_Grotesk({ subsets: ["latin"], variable: "--font-grotesk" });
const jetbrains = JetBrains_Mono({ subsets: ["latin"], variable: "--font-jetbrains" });

export const metadata: Metadata = {
  title: "RiskPulse",
  description: "Zero-Latency Contextual Risk and Safety Layer for AI Agents",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${grotesk.variable} ${jetbrains.variable}`}>
      <body className="font-sans">
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
