// Rosters do First Stand 2026
// ⚠ Confirmar gameName#tagLine exatos via Riot client antes de sincronizar

export interface Player {
  key: string;          // "GameName#TAG" (conta principal)
  gameName: string;
  tagLine: string;
  display: string;      // nome de exibição
  role: "TOP" | "JUNGLE" | "MIDDLE" | "BOTTOM" | "SUPPORT";
  region: string;
  routing: "americas" | "asia" | "europe" | "sea";
  alts?: { gameName: string; tagLine: string }[];  // contas secundárias/smurfs
}

export interface Team {
  name: string;
  shortName: string;
  region: string;       // CBLOL, LCK, LPL, LCS, APAC
  color: string;
  cnOnly?: boolean;     // CN teams: sem acesso via Riot API
  players: Player[];
}

const BR = (display: string, gameName: string, tagLine: string, role: Player["role"]): Player => ({
  key: `${gameName}#${tagLine}`,
  gameName, tagLine, display, role,
  region: "br1",
  routing: "americas",
});

const KR = (display: string, gameName: string, tagLine: string, role: Player["role"]): Player => ({
  key: `${gameName}#${tagLine}`,
  gameName, tagLine, display, role,
  region: "kr",
  routing: "asia",
});

const NA = (display: string, gameName: string, tagLine: string, role: Player["role"]): Player => ({
  key: `${gameName}#${tagLine}`,
  gameName, tagLine, display, role,
  region: "na1",
  routing: "americas",
});

const SEA = (display: string, gameName: string, tagLine: string, role: Player["role"]): Player => ({
  key: `${gameName}#${tagLine}`,
  gameName, tagLine, display, role,
  region: "sg2",
  routing: "sea",
});

export const TEAMS: Team[] = [
  {
    name: "LOUD",
    shortName: "LOUD",
    region: "CBLOL",
    color: "#00FF87",
    players: [
      { ...BR("xyno",    "xyno",           "kiwi", "TOP"),    alts: [{ gameName: "daniel ceasar", tagLine: "mari" }] },
      { ...BR("YoungJae","YoungDisney",     "LOUD", "JUNGLE"), alts: [{ gameName: "Pigbert",        tagLine: "LOUD" }] },
      BR("Envy",    "potato the cat", "envy", "MIDDLE"),
      BR("Bull",    "Capoeira rei",   "2003", "BOTTOM"),
      BR("RedBert", "RedBert",         "BR1", "SUPPORT"),
    ],
  },
  {
    name: "Gen.G",
    shortName: "GEN",
    region: "LCK",
    color: "#C89B3C",
    players: [
      KR("Doran",   "Doran",   "KR1",  "TOP"),
      KR("Peanut",  "Peanut",  "KR1",  "JUNGLE"),
      KR("Chovy",   "Chovy",   "KR1",  "MIDDLE"),
      KR("Peyz",    "Peyz",    "KR1",  "BOTTOM"),
      KR("Lehends", "Lehends", "KR1",  "SUPPORT"),
    ],
  },
  {
    name: "BNK FearX",
    shortName: "FRX",
    region: "LCK",
    color: "#0057A8",
    players: [
      KR("Kiin",   "Kiin",   "KR1", "TOP"),
      KR("Canyon", "Canyon", "KR1", "JUNGLE"),
      KR("Bdd",    "Bdd",    "KR1", "MIDDLE"),
      KR("Aiming", "Aiming", "KR1", "BOTTOM"),
      KR("Effort", "Effort", "KR1", "SUPPORT"),
    ],
  },
  {
    name: "Bilibili Gaming",
    shortName: "BLG",
    region: "LPL",
    color: "#00A1D6",
    cnOnly: true,
    players: [],
  },
  {
    name: "JD Gaming",
    shortName: "JDG",
    region: "LPL",
    color: "#E60012",
    cnOnly: true,
    players: [],
  },
  {
    name: "Team Thales",
    shortName: "THL",
    region: "APAC",
    color: "#00C4B4",
    players: [
      SEA("Stark",    "Stark",    "THL", "TOP"),
      SEA("Jlan",     "Jlan",     "THL", "JUNGLE"),
      SEA("Sybol",    "Sybol",    "THL", "MIDDLE"),
      SEA("Config",   "Config",   "THL", "BOTTOM"),
      SEA("Duality",  "Duality",  "THL", "SUPPORT"),
    ],
  },
  {
    name: "Lyon",
    shortName: "LYN",
    region: "LCS",
    color: "#7B2D8B",
    players: [
      NA("Dhokla",   "Dhokla",   "NA1", "TOP"),
      NA("Contractz","Contractz","NA1", "JUNGLE"),
      NA("Palafox",  "Palafox",  "NA1", "MIDDLE"),
      NA("Tomo",     "Tomo",     "NA1", "BOTTOM"),
      NA("Olleh",    "Olleh",    "NA1", "SUPPORT"),
    ],
  },
];

export const HOME_TEAM = "LOUD";

export const TEAM_BY_NAME: Record<string, Team> = Object.fromEntries(
  TEAMS.map(t => [t.name, t])
);

export const LOUD_PLAYERS: Player[] = TEAMS.find(t => t.name === "LOUD")!.players;

export const ROLE_ORDER = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "SUPPORT"] as const;
export const ROLE_SHORT: Record<string, string> = {
  TOP: "TOP", JUNGLE: "JGL", MIDDLE: "MID", BOTTOM: "ADC", SUPPORT: "SUP",
};
