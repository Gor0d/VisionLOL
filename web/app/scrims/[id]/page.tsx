import { notFound } from "next/navigation";
import { supabase, SessionPlayer } from "@/lib/supabase";

export const revalidate = 60;

const ROLE_ORDER = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "SUPPORT"];
const ROLE_SHORT: Record<string, string> = {
  TOP: "TOP", JUNGLE: "JGL", MIDDLE: "MID", BOTTOM: "ADC", SUPPORT: "SUP",
};

function kdaColor(kda: number) {
  return kda >= 3 ? "kda-good" : kda >= 2 ? "kda-ok" : "kda-bad";
}

async function getSession(id: string) {
  const { data: session } = await supabase
    .from("scrim_sessions")
    .select("*")
    .eq("id", id)
    .single();
  if (!session) return null;

  const { data: players } = await supabase
    .from("session_players")
    .select("*")
    .eq("session_id", id)
    .order("role");

  return { session, players: players ?? [] };
}

export default async function ScrimSessionPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const result = await getSession(id);
  if (!result) notFound();

  const { session, players } = result;
  const sortedPlayers = [...players].sort((a, b) =>
    ROLE_ORDER.indexOf(a.role) - ROLE_ORDER.indexOf(b.role)
  );

  const totalGames = session.wins + session.losses;
  const wr = totalGames > 0 ? Math.round((session.wins / totalGames) * 100) : 0;

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ fontSize: 11, color: "#404040", marginBottom: 6, letterSpacing: "0.1em" }}>
          // SESSÃO DE SCRIM
        </div>
        <div style={{ display: "flex", alignItems: "baseline", gap: 16, flexWrap: "wrap" }}>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "#e0e0e0" }}>
            LOUD <span style={{ color: "#505050" }}>vs</span>{" "}
            <span style={{ color: "#FF9830" }}>{session.opponent}</span>
          </h1>
          <span style={{ fontSize: 12, color: "#505050" }}>{session.date}</span>
        </div>

        <div style={{ display: "flex", gap: 12, marginTop: 12, alignItems: "center", flexWrap: "wrap" }}>
          <span className="badge badge-win">{session.wins}W</span>
          <span className="badge badge-loss">{session.losses}L</span>
          <span style={{ fontSize: 12, color: "#505050" }}>{wr}% WR</span>
          {session.notes && (
            <span style={{ fontSize: 12, color: "#606060", fontStyle: "italic" }}>{session.notes}</span>
          )}
        </div>
      </div>

      {/* Players table */}
      {sortedPlayers.length > 0 ? (
        <div>
          <div style={{ fontSize: 11, color: "#404040", letterSpacing: "0.1em", marginBottom: 12 }}>
            // JOGADORES
          </div>
          <table className="nerv-table" style={{ marginBottom: 32 }}>
            <thead>
              <tr>
                <th>ROLE</th>
                <th>JOGADOR</th>
                <th>CAMPEÃO</th>
                <th>JOGOS</th>
                <th>KDA</th>
                <th>CS/MIN</th>
                <th>VISION/MIN</th>
                <th>WIN%</th>
              </tr>
            </thead>
            <tbody>
              {sortedPlayers.map((p: SessionPlayer) => {
                const winRate = p.games > 0 ? Math.round((p.wins / p.games) * 100) : 0;
                return (
                  <tr key={p.id}>
                    <td>
                      <span className={`role-badge role-${p.role}`}>
                        {ROLE_SHORT[p.role] ?? p.role}
                      </span>
                    </td>
                    <td style={{ fontWeight: 500 }}>
                      {p.display || p.game_name}
                      <span style={{ color: "#404040", fontSize: 11 }}> #{p.tag_line}</span>
                    </td>
                    <td style={{ color: "#e0e0e0" }}>{p.top_champ || "—"}</td>
                    <td style={{ color: "#606060" }}>{p.games}</td>
                    <td>
                      <span className={kdaColor(p.kda_ratio)}>
                        {p.kda_ratio.toFixed(2)}
                      </span>
                      <span style={{ color: "#404040", fontSize: 11, marginLeft: 6 }}>
                        ({p.kills}/{p.deaths}/{p.assists})
                      </span>
                    </td>
                    <td style={{ color: "#808080" }}>{p.cs_per_min.toFixed(1)}</td>
                    <td style={{ color: "#808080" }}>{p.vision_pm.toFixed(1)}</td>
                    <td>
                      <span style={{ color: winRate >= 50 ? "#50FF50" : "#FF4040" }}>
                        {winRate}%
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="nerv-card" style={{ color: "#505050", textAlign: "center", padding: 32 }}>
          Sem dados de jogadores para esta sessão
        </div>
      )}

      {/* Raw metadata */}
      {session.metadata && Object.keys(session.metadata).length > 0 && (
        <details style={{ marginTop: 24 }}>
          <summary style={{ fontSize: 11, color: "#404040", cursor: "pointer", letterSpacing: "0.1em" }}>
            // METADATA RAW
          </summary>
          <pre style={{
            marginTop: 8,
            padding: 16,
            background: "#080808",
            border: "1px solid #181818",
            borderRadius: 3,
            fontSize: 11,
            color: "#505050",
            overflow: "auto",
          }}>
            {JSON.stringify(session.metadata, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
}
