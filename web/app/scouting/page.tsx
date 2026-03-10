import { supabase, ChampionPoolEntry } from "@/lib/supabase";

export const revalidate = 120;

const TEAMS = [
  { name: "Gen.G",             region: "LCK", color: "#C89B3C" },
  { name: "BNK FearX",         region: "LCK", color: "#0057A8" },
  { name: "Bilibili Gaming",   region: "LPL", color: "#00A1D6", cnOnly: true },
  { name: "JD Gaming",         region: "LPL", color: "#E60012", cnOnly: true },
  { name: "Team Thales",       region: "APAC",color: "#00C4B4" },
  { name: "Lyon",              region: "LCS", color: "#7B2D8B" },
];

const ROLE_ORDER = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "SUPPORT"];
const ROLE_SHORT: Record<string, string> = {
  TOP: "TOP", JUNGLE: "JGL", MIDDLE: "MID", BOTTOM: "ADC", SUPPORT: "SUP",
};

async function getPool(): Promise<ChampionPoolEntry[]> {
  const { data } = await supabase
    .from("champion_pool_cache")
    .select("*")
    .order("games", { ascending: false });
  return data ?? [];
}

function WinRateBar({ wr }: { wr: number }) {
  const color = wr >= 60 ? "#50FF50" : wr >= 50 ? "#FF9830" : "#FF4040";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div style={{ flex: 1, height: 4, background: "#1a1a1a", borderRadius: 2, overflow: "hidden" }}>
        <div style={{ width: `${wr}%`, height: "100%", background: color, transition: "width 0.5s" }} />
      </div>
      <span style={{ fontSize: 10, color, width: 30 }}>{wr}%</span>
    </div>
  );
}

export default async function ScoutingPage() {
  const pool = await getPool();

  // Group pool by player_key
  const byPlayer: Record<string, ChampionPoolEntry[]> = {};
  for (const entry of pool) {
    if (!byPlayer[entry.player_key]) byPlayer[entry.player_key] = [];
    byPlayer[entry.player_key].push(entry);
  }

  const hasData = pool.length > 0;

  return (
    <div>
      <div style={{ marginBottom: 32 }}>
        <div style={{ fontSize: 11, color: "#404040", letterSpacing: "0.1em", marginBottom: 6 }}>// MÓDULO 02</div>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: "#20F0FF" }}>SCOUTING — FIRST STAND 2026</h1>
        <p style={{ color: "#505050", fontSize: 12, marginTop: 4 }}>
          Análise de adversários da LOUD no First Stand 2026
        </p>
      </div>

      {/* Teams grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 12, marginBottom: 40 }}>
        {TEAMS.map(team => {
          // Find players for this team from pool (player_key format: "GameName#TAG")
          const teamPlayers = Object.entries(byPlayer).filter(([key]) =>
            pool.some(e => e.player_key === key && e.role)
          );

          return (
            <div key={team.name} className="nerv-card" style={{ borderTop: `2px solid ${team.color}` }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 12 }}>
                <span style={{ fontWeight: 700, color: "#e0e0e0" }}>{team.name}</span>
                <span style={{ fontSize: 10, color: "#505050", border: "1px solid #222", padding: "1px 6px", borderRadius: 2 }}>
                  {team.region}
                </span>
              </div>

              {team.cnOnly ? (
                <div style={{ padding: "12px 0", color: "#505050", fontSize: 11 }}>
                  ⚠ API da Riot não cobre a China (Tencent).<br />
                  <span style={{ color: "#404040" }}>Dados indisponíveis via API.</span>
                </div>
              ) : (
                <div style={{ color: "#404040", fontSize: 11 }}>
                  <div style={{ marginBottom: 6 }}>
                    Use o VisionLOL para buscar dados deste time.
                  </div>
                  {hasData && (
                    <span style={{ color: "#505050" }}>{teamPlayers.length} jogadores com dados</span>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Champion Pool table */}
      {hasData ? (
        <div>
          <div style={{ fontSize: 11, color: "#404040", letterSpacing: "0.1em", marginBottom: 12 }}>
            // CHAMPION POOL — DADOS COLETADOS
          </div>
          <table className="nerv-table">
            <thead>
              <tr>
                <th>JOGADOR</th>
                <th>ROLE</th>
                <th>CAMPEÃO</th>
                <th>JOGOS</th>
                <th>WIN RATE</th>
                <th>KDA</th>
              </tr>
            </thead>
            <tbody>
              {pool.slice(0, 50).map(entry => {
                const wr = entry.games > 0 ? Math.round((entry.wins / entry.games) * 100) : 0;
                return (
                  <tr key={entry.id}>
                    <td style={{ color: "#e0e0e0" }}>{entry.player_key}</td>
                    <td>
                      <span className={`role-badge role-${entry.role}`}>
                        {ROLE_SHORT[entry.role] ?? entry.role}
                      </span>
                    </td>
                    <td style={{ fontWeight: 500, color: "#e0e0e0" }}>{entry.champ}</td>
                    <td style={{ color: "#606060" }}>{entry.games}</td>
                    <td style={{ minWidth: 100 }}>
                      <WinRateBar wr={wr} />
                    </td>
                    <td className={entry.kda >= 3 ? "kda-good" : entry.kda >= 2 ? "kda-ok" : "kda-bad"}>
                      {entry.kda.toFixed(2)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="nerv-card" style={{ textAlign: "center", padding: 48, color: "#404040" }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>◈</div>
          <p style={{ color: "#606060", marginBottom: 8 }}>Champion pool ainda não coletada</p>
          <p style={{ fontSize: 12 }}>
            Na aba <span style={{ color: "#20F0FF" }}>🔍 Scouting</span> do VisionLOL,
            selecione um time e clique em "Atualizar" para coletar os dados
          </p>
        </div>
      )}
    </div>
  );
}
