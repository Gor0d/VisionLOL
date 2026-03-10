"use client";

import { useEffect, useState, useCallback } from "react";
import { createClient } from "@supabase/supabase-js";
import ObjectiveTimeline, { type GameEvent } from "@/components/ObjectiveTimeline";
import GoldDiffBar from "@/components/GoldDiffBar";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

interface PlayerState {
  player_id: string;
  game_time: number;
  champion: string;
  current_gold: number;
  kills: number;
  deaths: number;
  assists: number;
  cs: number;
  level: number;
  team: string;
  all_players: AllPlayer[];
  events: GameEvent[];
  is_active: boolean;
  updated_at: string;
}

interface AllPlayer {
  championName: string;
  summonerName: string;
  kills: number;
  deaths: number;
  assists: number;
  creepScore: number;
  level: number;
  team: string;
  position: string;
}

// Gold history per player for sparkline
type GoldHistory = Record<string, { t: number; gold: number }[]>;

const ROLE_ORDER = ["TOP", "JUNGLE", "MID", "BOT", "SUPPORT", ""];
const TEAM_COLOR = { ORDER: "#20F0FF", CHAOS: "#FF4040" };

function fmt(secs: number) {
  const m = Math.floor(secs / 60);
  const s = Math.floor(secs % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

function kdaColor(kda: number) {
  if (kda >= 4) return "#50FF50";
  if (kda >= 2.5) return "#FF9830";
  return "#e0e0e0";
}

function staleness(updatedAt: string): "fresh" | "stale" | "dead" {
  const diff = Date.now() - new Date(updatedAt).getTime();
  if (diff < 15_000) return "fresh";
  if (diff < 60_000) return "stale";
  return "dead";
}

export default function LiveBoard({ initialMatchKey }: { initialMatchKey?: string }) {
  const [matchKey, setMatchKey]     = useState<string | null>(initialMatchKey ?? null);
  const [players, setPlayers]       = useState<PlayerState[]>([]);
  const [goldHistory, setGoldHistory] = useState<GoldHistory>({});
  const [activeMatches, setActiveMatches] = useState<string[]>([]);
  const [lastUpdate, setLastUpdate] = useState<string>("");

  // Merge incoming state into players array
  const mergePlayer = useCallback((incoming: PlayerState) => {
    setPlayers(prev => {
      const idx = prev.findIndex(p => p.player_id === incoming.player_id);
      if (idx === -1) return [...prev, incoming];
      const next = [...prev];
      next[idx] = incoming;
      return next;
    });

    // Append to gold history (only if gold data available)
    if (incoming.current_gold > 0) {
      setGoldHistory(prev => {
        const key = incoming.player_id;
        const history = prev[key] ?? [];
        const last = history[history.length - 1];
        if (last && Math.abs(last.t - incoming.game_time) < 3) return prev; // debounce
        return {
          ...prev,
          [key]: [...history, { t: incoming.game_time, gold: incoming.current_gold }].slice(-60),
        };
      });
    }

    setLastUpdate(new Date().toLocaleTimeString("pt-BR"));
  }, []);

  // Poll active matches when none selected
  useEffect(() => {
    if (matchKey) return;
    const poll = async () => {
      const res = await fetch("/api/live/active");
      if (!res.ok) return;
      const json = await res.json();
      const keys = (json.active ?? []).map((m: any) => m.match_key);
      setActiveMatches(keys);
      if (keys.length === 1) setMatchKey(keys[0]);
    };
    poll();
    const t = setInterval(poll, 5000);
    return () => clearInterval(t);
  }, [matchKey]);

  // Load initial state when match_key is known
  useEffect(() => {
    if (!matchKey) return;
    fetch(`/api/live/${matchKey}`)
      .then(r => r.json())
      .then(json => {
        for (const p of json.players ?? []) mergePlayer(p);
      });
  }, [matchKey, mergePlayer]);

  // Supabase Realtime subscription
  useEffect(() => {
    if (!matchKey) return;

    const channel = supabase
      .channel(`live:${matchKey}`)
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "live_match_state",
          filter: `match_key=eq.${matchKey}`,
        },
        (payload) => {
          if (payload.new) mergePlayer(payload.new as PlayerState);
        }
      )
      .subscribe();

    return () => { supabase.removeChannel(channel); };
  }, [matchKey, mergePlayer]);

  // Merge all_players from the most up-to-date snapshot to show full 10-player view
  const allPlayersSnapshot: AllPlayer[] = (() => {
    const freshest = [...players].sort(
      (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
    )[0];
    return freshest?.all_players ?? [];
  })();

  // Merge all events across players, dedup by EventID
  const allEvents: GameEvent[] = (() => {
    const seen = new Set<number>();
    const out: GameEvent[] = [];
    for (const p of players) {
      for (const ev of p.events ?? []) {
        const id = ev.EventID ?? ev.EventTime;
        if (!seen.has(id as number)) {
          seen.add(id as number);
          out.push(ev);
        }
      }
    }
    return out.sort((a, b) => a.EventTime - b.EventTime);
  })();

  const gameTime = Math.max(...players.map(p => p.game_time), 0);

  // ── No match selected ──────────────────────────────────────────────
  if (!matchKey) {
    return (
      <div style={{ textAlign: "center", padding: "80px 0", color: "#404040" }}>
        <div style={{ fontSize: 40, marginBottom: 16 }}>◈</div>
        {activeMatches.length === 0 ? (
          <>
            <p style={{ color: "#505050", marginBottom: 8 }}>Nenhuma partida ao vivo detectada</p>
            <p style={{ fontSize: 11, color: "#303030" }}>
              Inicie o VisionLOL Agent nas máquinas dos jogadores para transmitir dados ao vivo
            </p>
          </>
        ) : (
          <div>
            <p style={{ color: "#505050", marginBottom: 16 }}>Selecione uma partida:</p>
            {activeMatches.map(k => (
              <button
                key={k}
                onClick={() => setMatchKey(k)}
                style={{
                  display: "block", margin: "8px auto",
                  padding: "8px 24px", background: "#0a0a0a",
                  border: "1px solid #333", borderRadius: 3,
                  color: "#FF9830", fontSize: 12, cursor: "pointer",
                  fontFamily: "inherit",
                }}
              >{k}</button>
            ))}
          </div>
        )}
      </div>
    );
  }

  // ── Live board ────────────────────────────────────────────────────
  return (
    <div>
      {/* Header bar */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24 }}>
        <div className="live-pulse" />
        <span style={{ fontWeight: 700, color: "#e0e0e0", fontSize: 13 }}>{matchKey}</span>
        <span style={{ color: "#FF9830", fontWeight: 700, fontSize: 15, fontVariantNumeric: "tabular-nums" }}>
          {fmt(gameTime)}
        </span>
        <span style={{ marginLeft: "auto", fontSize: 10, color: "#303030" }}>
          atualizado {lastUpdate}
        </span>
        <button
          onClick={() => { setMatchKey(null); setPlayers([]); setGoldHistory({}); }}
          style={{
            padding: "4px 10px", background: "transparent",
            border: "1px solid #222", borderRadius: 2,
            color: "#505050", fontSize: 10, cursor: "pointer", fontFamily: "inherit",
          }}
        >← voltar</button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 300px", gap: 16 }}>
        {/* ── Left: Player stats ── */}
        <div>
          {/* Our tracked players */}
          <div style={{ fontSize: 11, color: "#404040", letterSpacing: "0.1em", marginBottom: 10 }}>
            // JOGADORES MONITORADOS
          </div>
          <div style={{ marginBottom: 20 }}>
            {players.length === 0 ? (
              <div className="nerv-card" style={{ color: "#303030", fontSize: 11, textAlign: "center", padding: 24 }}>
                Aguardando dados dos agentes…
              </div>
            ) : (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead>
                  <tr style={{ color: "#404040", fontSize: 10 }}>
                    <th style={{ textAlign: "left", padding: "4px 8px" }}>JOGADOR</th>
                    <th style={{ textAlign: "left", padding: "4px 8px" }}>CAMPEÃO</th>
                    <th style={{ padding: "4px 8px" }}>LVL</th>
                    <th style={{ padding: "4px 8px" }}>KDA</th>
                    <th style={{ padding: "4px 8px" }}>CS</th>
                    <th style={{ padding: "4px 8px" }}>OURO</th>
                    <th style={{ padding: "4px 8px" }}>STATUS</th>
                  </tr>
                </thead>
                <tbody>
                  {players.map(p => {
                    const kda = (p.kills + p.assists) / Math.max(p.deaths, 1);
                    const freshness = staleness(p.updated_at);
                    const cspm = p.game_time > 0 ? (p.cs / (p.game_time / 60)).toFixed(1) : "—";
                    return (
                      <tr key={p.player_id} style={{ borderBottom: "1px solid #0d0d0d" }}>
                        <td style={{ padding: "6px 8px", color: TEAM_COLOR[p.team as "ORDER" | "CHAOS"] ?? "#e0e0e0", fontWeight: 600 }}>
                          {p.player_id.split("#")[0]}
                        </td>
                        <td style={{ padding: "6px 8px", color: "#e0e0e0" }}>{p.champion}</td>
                        <td style={{ padding: "6px 8px", textAlign: "center", color: "#606060" }}>{p.level}</td>
                        <td style={{ padding: "6px 8px", textAlign: "center", color: kdaColor(kda) }}>
                          {p.kills}/{p.deaths}/{p.assists}
                        </td>
                        <td style={{ padding: "6px 8px", textAlign: "center", color: "#606060" }}>
                          {p.cs} <span style={{ fontSize: 9, color: "#303030" }}>({cspm}/m)</span>
                        </td>
                        <td style={{ padding: "6px 8px", textAlign: "center", color: "#FF9830" }}>
                          {p.current_gold > 0 ? `${p.current_gold.toLocaleString("pt-BR")}` : "—"}
                        </td>
                        <td style={{ padding: "6px 8px", textAlign: "center" }}>
                          <span style={{
                            fontSize: 9, padding: "1px 5px", borderRadius: 2,
                            background: freshness === "fresh" ? "#50FF5022" : freshness === "stale" ? "#FF983022" : "#FF404022",
                            color: freshness === "fresh" ? "#50FF50" : freshness === "stale" ? "#FF9830" : "#FF4040",
                          }}>
                            {freshness === "fresh" ? "LIVE" : freshness === "stale" ? "~15s" : "OFFLINE"}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>

          {/* Gold sparklines */}
          {Object.keys(goldHistory).length > 0 && (
            <div>
              <div style={{ fontSize: 11, color: "#404040", letterSpacing: "0.1em", marginBottom: 10 }}>
                // EVOLUÇÃO DE OURO
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 16 }}>
                {Object.entries(goldHistory).map(([pid, hist]) => (
                  <div key={pid} className="nerv-card" style={{ padding: "10px 12px" }}>
                    <div style={{ fontSize: 10, color: "#606060", marginBottom: 6 }}>
                      {pid.split("#")[0]}
                    </div>
                    <GoldDiffBar series={hist} color="#FF9830" width={160} height={36} />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* All 10 players snapshot */}
          {allPlayersSnapshot.length > 0 && (
            <div style={{ marginTop: 20 }}>
              <div style={{ fontSize: 11, color: "#404040", letterSpacing: "0.1em", marginBottom: 10 }}>
                // TODOS OS JOGADORES
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                {(["ORDER", "CHAOS"] as const).map(side => (
                  <div key={side} className="nerv-card" style={{ borderTop: `2px solid ${TEAM_COLOR[side]}` }}>
                    <div style={{ fontWeight: 700, fontSize: 11, color: TEAM_COLOR[side], marginBottom: 8 }}>
                      {side === "ORDER" ? "⚔ EQUIPE AZUL" : "🔴 EQUIPE VERMELHA"}
                    </div>
                    {allPlayersSnapshot.filter(p => p.team === side).map(p => {
                      const kda = (p.kills + p.assists) / Math.max(p.deaths, 1);
                      return (
                        <div key={p.summonerName} style={{
                          display: "flex", alignItems: "center", gap: 8,
                          padding: "4px 0", borderBottom: "1px solid #0d0d0d",
                          fontSize: 11,
                        }}>
                          <span style={{ flex: 1, color: "#e0e0e0" }}>
                            {p.championName}
                          </span>
                          <span style={{ color: "#606060" }}>
                            {p.summonerName.slice(0, 10)}
                          </span>
                          <span style={{ color: kdaColor(kda), minWidth: 52, textAlign: "right" }}>
                            {p.kills}/{p.deaths}/{p.assists}
                          </span>
                          <span style={{ color: "#505050", minWidth: 28, textAlign: "right" }}>
                            {p.creepScore}cs
                          </span>
                        </div>
                      );
                    })}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* ── Right: Timeline ── */}
        <div>
          <div style={{ fontSize: 11, color: "#404040", letterSpacing: "0.1em", marginBottom: 10 }}>
            // OBJETIVOS
          </div>
          <div className="nerv-card">
            <ObjectiveTimeline events={allEvents} gameTime={gameTime} />
          </div>
        </div>
      </div>
    </div>
  );
}
