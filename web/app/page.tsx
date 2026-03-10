import Link from "next/link";
import { supabase } from "@/lib/supabase";

async function getStats() {
  const { count: sessions } = await supabase
    .from("scrim_sessions")
    .select("*", { count: "exact", head: true });
  const { data: latest } = await supabase
    .from("v_session_summary")
    .select("*")
    .order("date", { ascending: false })
    .limit(3);
  return { sessions: sessions ?? 0, latest: latest ?? [] };
}

export const revalidate = 60;

export default async function Home() {
  const { sessions, latest } = await getStats();

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 40, borderBottom: "1px solid #1a1a1a", paddingBottom: 24 }}>
        <div style={{ fontSize: 11, color: "#404040", marginBottom: 8, letterSpacing: "0.1em" }}>
          // VISIONLOL — SISTEMA DE ANÁLISE
        </div>
        <h1 style={{ fontSize: 28, fontWeight: 700, color: "#FF9830", letterSpacing: "0.05em" }}>
          LOUD CBLOL 2026
        </h1>
        <p style={{ color: "#505050", marginTop: 8, fontSize: 12 }}>
          Dashboard de scrims e scouting de adversários
        </p>
      </div>

      {/* Stats row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginBottom: 40 }}>
        {[
          { label: "SESSÕES", value: sessions, color: "#FF9830" },
          { label: "STATUS", value: "ONLINE", color: "#50FF50" },
          { label: "TEMPORADA", value: "2026", color: "#20F0FF" },
        ].map(s => (
          <div key={s.label} className="nerv-card" style={{ textAlign: "center" }}>
            <div style={{ fontSize: 10, color: "#404040", letterSpacing: "0.1em", marginBottom: 6 }}>{s.label}</div>
            <div style={{ fontSize: 24, fontWeight: 700, color: s.color }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Quick nav */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 40 }}>
        <Link href="/scrims" style={{ textDecoration: "none" }}>
          <div className="nerv-card" style={{ cursor: "pointer", transition: "border-color 0.15s", borderColor: "#222" }}
               onMouseEnter={undefined}>
            <div style={{ fontSize: 11, color: "#404040", marginBottom: 8 }}>▶ MÓDULO 01</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: "#FF9830", marginBottom: 8 }}>SCRIMS</div>
            <div style={{ fontSize: 12, color: "#505050" }}>
              Sessões de treino, KDA por jogador, champion stats e timeline de partidas
            </div>
          </div>
        </Link>
        <Link href="/scouting" style={{ textDecoration: "none" }}>
          <div className="nerv-card">
            <div style={{ fontSize: 11, color: "#404040", marginBottom: 8 }}>▶ MÓDULO 02</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: "#20F0FF", marginBottom: 8 }}>SCOUTING</div>
            <div style={{ fontSize: 12, color: "#505050" }}>
              First Stand 2026 — champion pools e análise de adversários por role
            </div>
          </div>
        </Link>
      </div>

      {/* Latest sessions */}
      {latest.length > 0 && (
        <div>
          <div style={{ fontSize: 11, color: "#404040", letterSpacing: "0.1em", marginBottom: 12 }}>
            // SESSÕES RECENTES
          </div>
          <table className="nerv-table">
            <thead>
              <tr>
                <th>DATA</th>
                <th>ADVERSÁRIO</th>
                <th>RESULTADO</th>
                <th>AVG KDA</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {latest.map((s: any) => (
                <tr key={s.id}>
                  <td style={{ color: "#606060" }}>{s.date}</td>
                  <td style={{ color: "#e0e0e0", fontWeight: 500 }}>{s.opponent}</td>
                  <td>
                    <span className="badge badge-win">{s.wins}W</span>
                    {" "}
                    <span className="badge badge-loss">{s.losses}L</span>
                  </td>
                  <td>
                    <span className={s.avg_kda >= 3 ? "kda-good" : s.avg_kda >= 2 ? "kda-ok" : "kda-bad"}>
                      {(s.avg_kda ?? 0).toFixed(2)}
                    </span>
                  </td>
                  <td>
                    <Link href={`/scrims/${s.id}`} style={{ fontSize: 11, color: "#FF9830" }}>
                      ver →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {sessions === 0 && (
        <div className="nerv-card" style={{ textAlign: "center", padding: 40, color: "#404040" }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>◈</div>
          <div style={{ fontSize: 14, marginBottom: 8, color: "#606060" }}>Sem sessões publicadas</div>
          <div style={{ fontSize: 12 }}>
            Use o botão <span style={{ color: "#FF9830" }}>📤 Publicar</span> no VisionLOL para enviar dados aqui
          </div>
        </div>
      )}
    </div>
  );
}
