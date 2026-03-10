// Data Dragon utilities — safe para client e server

const FALLBACK_VERSION = "14.24.1";

// Versão cacheada em memória (atualizada a cada build)
let _version: string | null = null;

export async function getDDragonVersion(): Promise<string> {
  if (_version) return _version;
  try {
    const res = await fetch("https://ddragon.leagueoflegends.com/api/versions.json", {
      next: { revalidate: 86400 }, // 24h
    });
    const versions: string[] = await res.json();
    _version = versions[0];
    return _version;
  } catch {
    return FALLBACK_VERSION;
  }
}

// ── Correções de nome (Riot API → DDragon filename) ──────────────────
const NAME_FIXES: Record<string, string> = {
  MonkeyKing:     "Wukong",
  Nunu:           "Nunu",
  AurelionSol:    "AurelionSol",
  BelVeth:        "Belveth",
  ChoGath:        "Chogath",
  DrMundo:        "DrMundo",
  FiddleSticks:   "Fiddlesticks",
  JarvanIV:       "JarvanIV",
  KaiSa:          "Kaisa",
  KhaZix:         "Khazix",
  KogMaw:         "KogMaw",
  LeBlanc:        "Leblanc",
  LeeSin:         "LeeSin",
  MasterYi:       "MasterYi",
  MissFortune:    "MissFortune",
  RekSai:         "RekSai",
  TahmKench:      "TahmKench",
  TwistedFate:    "TwistedFate",
  VelKoz:         "Velkoz",
  XinZhao:        "XinZhao",
};

export function normalizeDDragonName(champion: string): string {
  return NAME_FIXES[champion] ?? champion;
}

export function championIconUrl(champion: string, version = FALLBACK_VERSION): string {
  const name = normalizeDDragonName(champion);
  return `https://ddragon.leagueoflegends.com/cdn/${version}/img/champion/${name}.png`;
}

export function championSplashUrl(champion: string): string {
  const name = normalizeDDragonName(champion);
  return `https://ddragon.leagueoflegends.com/cdn/img/champion/splash/${name}_0.jpg`;
}

export function championLoadingUrl(champion: string): string {
  const name = normalizeDDragonName(champion);
  return `https://ddragon.leagueoflegends.com/cdn/img/champion/loading/${name}_0.jpg`;
}

export function profileIconUrl(iconId: number, version = FALLBACK_VERSION): string {
  return `https://ddragon.leagueoflegends.com/cdn/${version}/img/profileicon/${iconId}.png`;
}

// Patch no formato "14.24" a partir de uma string de versão "14.24.1"
export function versionToPatch(version: string): string {
  const parts = version.split(".");
  return `${parts[0]}.${parts[1]}`;
}
