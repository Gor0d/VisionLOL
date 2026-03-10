import "server-only";

// ── Configuração ─────────────────────────────────────────────────────
const API_KEY = process.env.RIOT_API_KEY ?? "";

const ROUTING_BASE: Record<string, string> = {
  americas: "https://americas.api.riotgames.com",
  asia:     "https://asia.api.riotgames.com",
  europe:   "https://europe.api.riotgames.com",
  sea:      "https://sea.api.riotgames.com",
};

const SERVER_BASE: Record<string, string> = {
  br1: "https://br1.api.riotgames.com",
  kr:  "https://kr.api.riotgames.com",
  na1: "https://na1.api.riotgames.com",
  sg2: "https://sg2.api.riotgames.com",
  euw1:"https://euw1.api.riotgames.com",
  jp1: "https://jp1.api.riotgames.com",
  vn2: "https://vn2.api.riotgames.com",
};

// ── Tipos ─────────────────────────────────────────────────────────────

export interface RiotParticipant {
  puuid: string;
  summonerName: string;
  championName: string;
  teamPosition: string;     // "TOP","JUNGLE","MIDDLE","BOTTOM","UTILITY"
  kills: number;
  deaths: number;
  assists: number;
  totalMinionsKilled: number;
  neutralMinionsKilled: number;
  visionScore: number;
  goldEarned: number;
  totalDamageDealtToChampions: number;
  win: boolean;
  teamId: number;
  individualPosition: string;
  lane: string;
}

export interface RiotMatchInfo {
  gameId: number;
  gameVersion: string;
  gameDuration: number;     // seconds
  gameStartTimestamp: number;
  queueId: number;
  participants: RiotParticipant[];
}

export interface RiotMatch {
  metadata: { matchId: string; participants: string[] };
  info: RiotMatchInfo;
}

// ── Delay para rate limit (dev key: 20 req/s) ─────────────────────────
const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));

// ── Fetcher central ───────────────────────────────────────────────────
async function riotFetch<T>(url: string, retries = 1): Promise<T> {
  if (!API_KEY) throw new Error("RIOT_API_KEY não configurada");

  const fullUrl = url.includes("?") ? `${url}&api_key=${API_KEY}` : `${url}?api_key=${API_KEY}`;
  const res = await fetch(fullUrl, { next: { revalidate: 0 } });

  if (res.status === 429) {
    if (retries <= 0) throw new Error("Riot API rate limit atingido");
    const retry = Number(res.headers.get("Retry-After") ?? "1");
    await sleep(retry * 1000 + 100);
    return riotFetch<T>(url, retries - 1);
  }

  if (res.status === 404) throw new Error(`404: ${url}`);
  if (!res.ok) throw new Error(`Riot API ${res.status}: ${url}`);

  return res.json() as Promise<T>;
}

// ── Account / PUUID ───────────────────────────────────────────────────

export async function getPuuid(
  gameName: string,
  tagLine: string,
  routing = "americas"
): Promise<string> {
  const base = ROUTING_BASE[routing];
  const data = await riotFetch<{ puuid: string }>(
    `${base}/riot/account/v1/accounts/by-riot-id/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}`
  );
  return data.puuid;
}

// ── Match IDs ─────────────────────────────────────────────────────────

export async function getMatchIds(
  puuid: string,
  routing: string,
  count = 20,
  queueId?: number
): Promise<string[]> {
  const base = ROUTING_BASE[routing];
  const queue = queueId ? `&queue=${queueId}` : "";
  return riotFetch<string[]>(
    `${base}/lol/match/v5/matches/by-puuid/${puuid}/ids?count=${count}${queue}`
  );
}

// ── Match detail ──────────────────────────────────────────────────────

export async function getMatch(matchId: string, routing: string): Promise<RiotMatch> {
  const base = ROUTING_BASE[routing];
  return riotFetch<RiotMatch>(`${base}/lol/match/v5/matches/${matchId}`);
}

// ── Helpers ───────────────────────────────────────────────────────────

export function normalizeRole(teamPosition: string): string {
  const map: Record<string, string> = {
    TOP:     "TOP",
    JUNGLE:  "JUNGLE",
    MIDDLE:  "MIDDLE",
    BOTTOM:  "BOTTOM",
    UTILITY: "SUPPORT",
  };
  return map[teamPosition] ?? teamPosition;
}

export function patchFromVersion(gameVersion: string): string {
  const parts = gameVersion.split(".");
  return `${parts[0]}.${parts[1]}`;
}

export function gameDateFromTimestamp(ts: number): string {
  return new Date(ts).toISOString().slice(0, 10);
}
