# -*- coding: utf-8 -*-
"""
Gerenciador de configuração do VisionLOL Agent.
Salva/carrega config em %APPDATA%/VisionLOLAgent/config.json
"""

import json
import os

_CONFIG_DIR  = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")),
                             "VisionLOLAgent")
_CONFIG_FILE = os.path.join(_CONFIG_DIR, "config.json")

_DEFAULTS = {
    "server_url":     "http://192.168.1.10:7654",
    "auth_token":     "",
    "player_riot_id": "",
}


def load() -> dict:
    """Carrega configuração do disco, mesclando com defaults."""
    os.makedirs(_CONFIG_DIR, exist_ok=True)
    try:
        with open(_CONFIG_FILE, encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(_DEFAULTS)
        merged.update(data)
        return merged
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(_DEFAULTS)


def save(cfg: dict) -> None:
    """Persiste configuração no disco."""
    os.makedirs(_CONFIG_DIR, exist_ok=True)
    with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
