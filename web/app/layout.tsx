import type { Metadata } from "next";
import { IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import Nav from "@/components/Nav";

const ibm = IBM_Plex_Mono({
  weight: ["400", "500", "700"],
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "VisionLOL Dashboard",
  description: "Análise de scrims e scouting para LOUD",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={ibm.className}>
      <body style={{ background: "#000", minHeight: "100vh" }}>
        <Nav />
        <main style={{ maxWidth: 1200, margin: "0 auto", padding: "24px 16px" }}>
          {children}
        </main>
        <footer style={{ borderTop: "1px solid #1a1a1a", padding: "12px 16px", textAlign: "center", color: "#404040", fontSize: 11, marginTop: 40 }}>
          VisionLOL — Sistema de análise de scrims · LOUD CBLOL 2026
        </footer>
      </body>
    </html>
  );
}
