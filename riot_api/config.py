# -*- coding: utf-8 -*-
"""
Configuracao e constantes para APIs da Riot Games
"""

import json
import os

# === URLs da Live Client API (localhost, durante o jogo) ===
LIVE_CLIENT_BASE_URL = "https://127.0.0.1:2999"
LIVE_CLIENT_ALLGAMEDATA = f"{LIVE_CLIENT_BASE_URL}/liveclientdata/allgamedata"
LIVE_CLIENT_PLAYERLIST = f"{LIVE_CLIENT_BASE_URL}/liveclientdata/playerlist"
LIVE_CLIENT_EVENTS = f"{LIVE_CLIENT_BASE_URL}/liveclientdata/eventdata"
LIVE_CLIENT_GAMESTATS = f"{LIVE_CLIENT_BASE_URL}/liveclientdata/gamestats"
LIVE_CLIENT_ACTIVE_PLAYER = f"{LIVE_CLIENT_BASE_URL}/liveclientdata/activeplayername"

# === URLs da Riot REST API ===
AMERICAS_BASE_URL = "https://americas.api.riotgames.com"
BR1_BASE_URL = "https://br1.api.riotgames.com"

# Match-V5 (americas routing para BR1)
MATCH_BY_PUUID = AMERICAS_BASE_URL + "/lol/match/v5/matches/by-puuid/{puuid}/ids"
MATCH_BY_ID = AMERICAS_BASE_URL + "/lol/match/v5/matches/{match_id}"
MATCH_TIMELINE = AMERICAS_BASE_URL + "/lol/match/v5/matches/{match_id}/timeline"

# Account-V1 (americas routing)
ACCOUNT_BY_RIOT_ID = AMERICAS_BASE_URL + "/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"

# Summoner-V4 (regional)
SUMMONER_BY_PUUID = BR1_BASE_URL + "/lol/summoner/v4/summoners/by-puuid/{puuid}"

# Spectator-V5 (regional) — 404 = não está em jogo
SPECTATOR_BY_PUUID = BR1_BASE_URL + "/lol/spectator/v5/active-games/by-summoner/{puuid}"

# === Constantes de proximidade ===
PROXIMITY_POLL_INTERVAL = 0.5       # segundos entre polls
GANK_DISTANCE_THRESHOLD = 2000      # unidades do mapa
GANK_DURATION_THRESHOLD = 5.0       # segundos minimos para considerar gank
MAP_SIZE = (14820, 14881)           # dimensoes do Summoner's Rift

# === Rate limiting ===
RATE_LIMIT_SHORT = 20    # requests por segundo (dev key)
RATE_LIMIT_LONG = 100    # requests por 2 minutos (dev key)

# === Caminho do config.json ===
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

# Config padrão
DEFAULT_CONFIG = {
    "riot_api_key": "",
    "game_name": "",
    "tag_line": "BR1",
    "region": "br1",
    "routing": "americas",
    "proximity": {
        "poll_interval": 0.5,
        "gank_distance": 2000,
        "gank_duration": 5.0
    },
    "auto_start_riot_tracking": False,
    "scrim_server": {
        "enabled": False,
        "port": 7654,
        "token": ""   # gerado automaticamente ao ativar pela primeira vez
    }
}


def load_config():
    """Carrega configuracao do config.json"""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        # Mescla com defaults para garantir que todas as chaves existem
        merged = DEFAULT_CONFIG.copy()
        merged.update(config)
        if "proximity" in config:
            merged["proximity"] = DEFAULT_CONFIG["proximity"].copy()
            merged["proximity"].update(config["proximity"])
        if "scrim_server" in config:
            merged["scrim_server"] = DEFAULT_CONFIG["scrim_server"].copy()
            merged["scrim_server"].update(config["scrim_server"])
        return merged
    except FileNotFoundError:
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    except json.JSONDecodeError:
        return DEFAULT_CONFIG.copy()


def save_config(config):
    """Salva configuracao no config.json"""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
