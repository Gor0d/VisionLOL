import Link from "next/link";
import { supabase, ScrimSession } from "@/lib/supabase";

export const revalidate = 60;

async function getSessions(): Promise<ScrimSession[]> {
  const { data } = await supabase
    .from("v_session_summary")
    .select("*")
    .order("date", { ascending: false });
  return data ?? [];
}

export default async function ScrimsPage() {
  const sessions = await getSessions();

  return (
    <div>
      <div style={{ marginBottom: 32 }}>
        <div style={{ fontSize: 11, color: "#404040", letterSpacing: "0.1em", marginBottom: 6 }}>// MÓDULO 01</div>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: "#FF9830" }}>SCRIMS</h1>
        <p style={{ color: "#505050", fontSize: 12, marginTop: 4 }}>
          {sessions.length} sessão{sessions.length !== 1 ? "ões" : ""} publicada{sessions.length !== 1 ? "s" : ""}
        </p>
      </div>

      {sessions.length === 0 ? (
        <div className="nerv-card" style={{ textAlign: "center", padding: 48, color: "#404040" }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>◈</div>
          <p style={{ color: "#606060", marginBottom: 8 }}>Nenhuma sessão publicada ainda</p>
          <p style={{ fontSize: 12 }}>Use o VisionLOL desktop para publicar scrims aqui</p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {sessions.map((s) => (
            <Link key={s.id} href={`/scrims/${s.id}`} style={{ textDecoration: "none" }}>
              <div style={{
                display: "grid",
                gridTemplateColumns: "90px 1fr 80px 80px 80px 60px",
                alignItems: "center",
                gap: 12,
                padding: "12px 16px",
                background: "#0a0a0a",
                border: "1px solid #181818",
                borderRadius: 3,
                cursor: "pointer",
                transition: "border-color 0.15s, background 0.15s",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor = "#333";
                (e.currentTarget as HTMLElement).style.background = "#0f0f0f";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor = "#181818";
                (e.currentTarget as HTMLElement).style.background = "#0a0a0a";
              }}>
                <div style={{ color: "#505050", fontSize: 11 }}>{s.date}</div>
                <div>
                  <span style={{ color: "#e0e0e0", fontWeight: 600 }}>vs {s.opponent}</span>
                  {s.notes && (
                    <span style={{ color: "#404040", fontSize: 11, marginLeft: 10 }}>{s.notes.slice(0, 40)}</span>
                  )}
                </div>
                <div>
                  <span className="badge badge-win">{s.wins}W</span>
                  {" "}
                  <span className="badge badge-loss">{s.losses}L</span>
                </div>
                <div style={{ fontSize: 11, color: "#505050" }}>
                  {s.player_count ?? 0} jogadores
                </div>
                <div>
                  <span style={{ fontSize: 11, color: "#404040" }}>KDA </span>
                  <span className={
                    (s.avg_kda ?? 0) >= 3 ? "kda-good" :
                    (s.avg_kda ?? 0) >= 2 ? "kda-ok" : "kda-bad"
                  }>
                    {(s.avg_kda ?? 0).toFixed(2)}
                  </span>
                </div>
                <div style={{ textAlign: "right", color: "#FF9830", fontSize: 12 }}>→</div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
