"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/",         label: "HOME" },
  { href: "/players",  label: "PLAYERS" },
  { href: "/scrims",   label: "SCRIMS" },
  { href: "/insights", label: "INSIGHTS" },
  { href: "/scouting", label: "SCOUTING" },
];

export default function Nav() {
  const path = usePathname();

  return (
    <header style={{
      borderBottom: "1px solid #1a1a1a",
      background: "#050505",
      position: "sticky",
      top: 0,
      zIndex: 100,
    }}>
      <div style={{
        maxWidth: 1200,
        margin: "0 auto",
        padding: "0 16px",
        display: "flex",
        alignItems: "center",
        gap: 32,
        height: 48,
      }}>
        {/* Logo */}
        <span style={{ color: "#FF9830", fontWeight: 700, fontSize: 15, letterSpacing: "0.1em" }}>
          ◈ VISION<span style={{ color: "#20F0FF" }}>LOL</span>
        </span>

        {/* Links */}
        <nav style={{ display: "flex", gap: 2 }}>
          {links.map(l => {
            const active = path === l.href || (l.href !== "/" && path.startsWith(l.href));
            return (
              <Link key={l.href} href={l.href} style={{
                padding: "0 12px",
                height: 48,
                display: "flex",
                alignItems: "center",
                fontSize: 11,
                fontWeight: 700,
                letterSpacing: "0.12em",
                color: active ? "#FF9830" : "#505050",
                borderBottom: `2px solid ${active ? "#FF9830" : "transparent"}`,
                transition: "color 0.15s, border-color 0.15s",
                textDecoration: "none",
              }}>
                {l.label}
              </Link>
            );
          })}
        </nav>

        <div style={{ marginLeft: "auto", fontSize: 10, color: "#303030" }}>
          CBLOL 2026
        </div>
      </div>
    </header>
  );
}
