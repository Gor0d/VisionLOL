# -*- coding: utf-8 -*-
"""
Dados estáticos do First Stand 2026.

HOME_TEAM = LOUD (CBLOL) — time base para comparação.
Os accounts dos jogadores adversários podem ser preenchidos via UI
e são persistidos em first_stand_roster.json.
"""

import os
import json

# ── Roteamento por região ──────────────────────────────────────────────
ROUTING_MAP: dict[str, str] = {
    "br1":   "americas",
    "la1":   "americas",
    "la2":   "americas",
    "na1":   "americas",
    "kr":    "asia",
    "jp1":   "asia",
    "euw1":  "europe",
    "eune1": "europe",
    "ru":    "europe",
    "tr1":   "europe",
    "vn2":   "sea",
    "sg2":   "sea",
    "th2":   "sea",
    "tw2":   "sea",
    "ph2":   "sea",
    "oc1":   "sea",
}

ROUTING_BASE: dict[str, str] = {
    "americas": "https://americas.api.riotgames.com",
    "asia":     "https://asia.api.riotgames.com",
    "europe":   "https://europe.api.riotgames.com",
    "sea":      "https://sea.api.riotgames.com",
}

# ── Time da casa ───────────────────────────────────────────────────────
HOME_TEAM = "LOUD"

# ── Slot vazio de jogador (preencher via UI) ───────────────────────────
def _slot(role: str, game_name: str = "", tag: str = "", region: str = "br1") -> dict:
    return {"role": role, "game_name": game_name, "tag": tag, "region": region}

# ── Times do First Stand 2025 ──────────────────────────────────────────
#
#  game_name / tag: deixar vazio para preencher via UI.
#  Valores pré-populados são informações públicas conhecidas.
#
FIRST_STAND_TEAMS: dict[str, dict] = {
    "LOUD": {
        "display":  "LOUD",
        "region":   "CBLOL",
        "server":   "br1",
        "color":    "#FF0000",          # vermelho LOUD
        "is_home":  True,
        "players": [
            _slot("TOP",     "xyno",           "kiwi", "br1"),
            _slot("JUNGLE",  "YoungDisney",    "LOUD",  "br1"),
            _slot("MIDDLE",  "potato the cat", "envy",  "br1"),
            _slot("BOTTOM",  "Capoeira rei",   "2003",  "br1"),
            _slot("SUPPORT", "RedBert",        "BR1",   "br1"),
        ],
    },
    "Gen.G": {
        "display":  "Gen.G",
        "region":   "LCK",
        "server":   "kr",
        "color":    "#C89B3C",          # dourado Gen.G
        "is_home":  False,
        "players": [
            _slot("TOP",     "Doran",   "KR1",  "kr"),
            _slot("JUNGLE",  "Peanut",  "KR1",  "kr"),
            _slot("MIDDLE",  "Chovy",   "KR1",  "kr"),
            _slot("BOTTOM",  "Peyz",    "KR1",  "kr"),
            _slot("SUPPORT", "Lehends", "KR1",  "kr"),
        ],
    },
    "BNK FearX": {
        "display":  "BNK FearX",
        "region":   "LCK",
        "server":   "kr",
        "color":    "#0057A8",          # azul BNK
        "is_home":  False,
        "players": [
            _slot("TOP",     "Kiin",   "KR1", "kr"),
            _slot("JUNGLE",  "Canyon", "KR1", "kr"),
            _slot("MIDDLE",  "Bdd",    "KR1", "kr"),
            _slot("BOTTOM",  "Aiming", "KR1", "kr"),
            _slot("SUPPORT", "Effort", "KR1", "kr"),
        ],
    },
    "Bilibili Gaming": {
        "display":  "Bilibili Gaming",
        "region":   "LPL",
        "server":   "cn",              # CN — sem acesso via API padrão
        "color":    "#00A1D6",          # azul Bilibili
        "is_home":  False,
        "cn_only":  True,              # flag: API da Riot não cobre CN
        "players": [
            _slot("TOP"),
            _slot("JUNGLE"),
            _slot("MIDDLE"),
            _slot("BOTTOM"),
            _slot("SUPPORT"),
        ],
    },
    "JD Gaming": {
        "display":  "JD Gaming",
        "region":   "LPL",
        "server":   "cn",
        "color":    "#E60012",          # vermelho JDG
        "is_home":  False,
        "cn_only":  True,
        "players": [
            _slot("TOP"),
            _slot("JUNGLE"),
            _slot("MIDDLE"),
            _slot("BOTTOM"),
            _slot("SUPPORT"),
        ],
    },
    "Team Thales": {
        "display":  "Team Thales",
        "region":   "APAC",
        "server":   "sg2",
        "color":    "#00C4B4",          # teal APAC
        "is_home":  False,
        "players": [
            _slot("TOP",     "", "", "sg2"),
            _slot("JUNGLE",  "", "", "sg2"),
            _slot("MIDDLE",  "", "", "sg2"),
            _slot("BOTTOM",  "", "", "sg2"),
            _slot("SUPPORT", "", "", "sg2"),
        ],
    },
    "Lyon": {
        "display":  "Lyon",
        "region":   "LCS",
        "server":   "na1",
        "color":    "#7B2D8B",          # roxo Lyon
        "is_home":  False,
        "players": [
            _slot("TOP",     "", "", "na1"),
            _slot("JUNGLE",  "", "", "na1"),
            _slot("MIDDLE",  "", "", "na1"),
            _slot("BOTTOM",  "", "", "na1"),
            _slot("SUPPORT", "", "", "na1"),
        ],
    },
}

# ── Persistência do roster (edições via UI) ────────────────────────────
_ROSTER_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "first_stand_roster.json"
)


def load_roster() -> dict:
    """Carrega o roster salvo (edições manuais), sobrepondo os defaults."""
    base = {k: json.loads(json.dumps(v)) for k, v in FIRST_STAND_TEAMS.items()}
    if not os.path.exists(_ROSTER_PATH):
        return base
    try:
        with open(_ROSTER_PATH, "r", encoding="utf-8") as f:
            saved = json.load(f)
        # Mescla: mantém times do default, sobrepõe jogadores salvos
        for team_name, team_data in saved.items():
            if team_name in base:
                base[team_name]["players"] = team_data.get(
                    "players", base[team_name]["players"]
                )
            else:
                base[team_name] = team_data
        return base
    except Exception:
        return base


def save_roster(teams: dict) -> None:
    """Persiste edições manuais dos jogadores."""
    to_save = {
        name: {"players": data["players"]}
        for name, data in teams.items()
    }
    with open(_ROSTER_PATH, "w", encoding="utf-8") as f:
        json.dump(to_save, f, indent=2, ensure_ascii=False)
