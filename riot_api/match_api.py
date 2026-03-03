# -*- coding: utf-8 -*-
"""
Wrapper para Riot Match-V5 e Account-V1 APIs
Acesso a historico de partidas, timelines e dados de conta
"""

import sys
import os
import math
import json
import time
import re
from urllib.parse import quote

from .config import (
    ACCOUNT_BY_RIOT_ID,
    MATCH_BY_PUUID,
    MATCH_BY_ID,
    MATCH_TIMELINE,
    SUMMONER_BY_PUUID,
    SPECTATOR_BY_PUUID,
)

# Cache em disco para evitar re-fetch de dados imutáveis (partidas encerradas)
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")

# Logger com fallback
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from logger import get_logger
    logger = get_logger("MatchAPI")
except Exception:
    class _DummyLogger:
        def debug(self, msg): pass
        def info(self, msg): print(f"[INFO] {msg}")
        def warning(self, msg): print(f"[WARNING] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
        def exception(self, msg): print(f"[EXCEPTION] {msg}")
    logger = _DummyLogger()


class MatchAPI:
    """Wrapper para Riot Match-V5 e Account-V1 APIs"""

    def __init__(self, http_client):
        self.http = http_client
        self._puuid_cache = {}
        os.makedirs(CACHE_DIR, exist_ok=True)

    # ─────────────────────────────────────────────────────────────────
    #  CACHE EM DISCO
    # ─────────────────────────────────────────────────────────────────

    def _cache_path(self, key: str) -> str:
        safe = re.sub(r"[^\w\-.]", "_", key)
        return os.path.join(CACHE_DIR, safe + ".json")

    def _load_cache(self, key: str, max_age_s: float | None = None):
        """Retorna dados do cache ou None se ausente/expirado."""
        try:
            with open(self._cache_path(key), encoding="utf-8") as f:
                entry = json.load(f)
            if max_age_s is not None and time.time() - entry.get("_ts", 0) > max_age_s:
                return None
            return entry.get("data")
        except Exception:
            return None

    def _save_cache(self, key: str, data) -> None:
        try:
            with open(self._cache_path(key), "w", encoding="utf-8") as f:
                json.dump({"_ts": time.time(), "data": data}, f, ensure_ascii=False)
        except Exception:
            pass

    def get_puuid(self, game_name, tag_line):
        """Obtem PUUID a partir de Riot ID (gameName#tagLine)"""
        mem_key  = f"{game_name}#{tag_line}"
        disk_key = f"puuid_{game_name}_{tag_line}"

        if mem_key in self._puuid_cache:
            return self._puuid_cache[mem_key]

        cached = self._load_cache(disk_key)
        if cached:
            self._puuid_cache[mem_key] = cached
            return cached

        url = ACCOUNT_BY_RIOT_ID.format(
            game_name=quote(game_name, safe=""),
            tag_line=quote(tag_line, safe=""),
        )
        data = self.http.get_riot(url)

        if data and "puuid" in data:
            self._puuid_cache[mem_key] = data["puuid"]
            self._save_cache(disk_key, data["puuid"])
            logger.info(f"PUUID obtido para {mem_key}: {data['puuid'][:8]}...")
            return data["puuid"]

        logger.error(f"Nao foi possivel obter PUUID para {mem_key}")
        return None

    def get_match_ids(self, puuid, count=10, queue=None, start=0):
        """Obtem lista de IDs de partidas recentes (cache com TTL de 5 min)"""
        disk_key = f"ids_{puuid}_{count}_{queue or 'all'}_{start}"
        cached = self._load_cache(disk_key, max_age_s=300)
        if cached is not None:
            logger.info(f"Match IDs do cache ({len(cached)} partidas)")
            return cached

        url = MATCH_BY_PUUID.format(puuid=puuid)
        params = {"count": count, "start": start}
        if queue is not None:
            params["queue"] = queue  # 420=Ranked Solo, 400=Normal Draft

        data = self.http.get_riot(url, params=params)

        if data is not None:
            logger.info(f"Encontradas {len(data)} partidas")
            self._save_cache(disk_key, data)
            return data

        logger.error("Nao foi possivel obter lista de partidas")
        return []

    def get_match_data(self, match_id):
        """Obtem dados completos de uma partida (imutável → cache permanente)"""
        cached = self._load_cache(f"match_{match_id}")
        if cached:
            return cached

        url = MATCH_BY_ID.format(match_id=match_id)
        data = self.http.get_riot(url)

        if data:
            logger.info(f"Dados da partida {match_id} obtidos")
            self._save_cache(f"match_{match_id}", data)
            return data

        logger.error(f"Nao foi possivel obter dados da partida {match_id}")
        return None

    def get_match_timeline(self, match_id):
        """Obtem timeline detalhada de uma partida (imutável → cache permanente)"""
        cached = self._load_cache(f"timeline_{match_id}")
        if cached:
            frames = cached.get("info", {}).get("frames", [])
            logger.info(f"Timeline de {match_id} do cache ({len(frames)} frames)")
            return cached

        url = MATCH_TIMELINE.format(match_id=match_id)
        data = self.http.get_riot(url)

        if data:
            frames = data.get("info", {}).get("frames", [])
            logger.info(f"Timeline de {match_id} obtida ({len(frames)} frames)")
            self._save_cache(f"timeline_{match_id}", data)
            return data

        logger.error(f"Nao foi possivel obter timeline de {match_id}")
        return None

    def get_participant_by_puuid(self, match_data, puuid):
        """Extrai dados do participante a partir do PUUID"""
        if not match_data:
            return None

        participants = match_data.get("info", {}).get("participants", [])
        for p in participants:
            if p.get("puuid") == puuid:
                return p

        return None

    def get_participant_id_by_puuid(self, match_data, puuid):
        """Obtem o participantId (1-10) a partir do PUUID"""
        if not match_data:
            return None

        participants = match_data.get("info", {}).get("participants", [])
        for p in participants:
            if p.get("puuid") == puuid:
                return p.get("participantId")

        # Tenta pela metadata
        metadata = match_data.get("metadata", {})
        puuid_list = metadata.get("participants", [])
        if puuid in puuid_list:
            return puuid_list.index(puuid) + 1

        return None

    def get_match_summary(self, match_data, puuid=None):
        """Retorna resumo legivel de uma partida"""
        if not match_data:
            return None

        info = match_data.get("info", {})
        duration = info.get("gameDuration", 0)
        minutes = duration // 60
        mode = info.get("gameMode", "UNKNOWN")

        summary = {
            "match_id": match_data.get("metadata", {}).get("matchId", ""),
            "mode": mode,
            "duration": f"{minutes}min",
            "duration_seconds": duration,
        }

        if puuid:
            participant = self.get_participant_by_puuid(match_data, puuid)
            if participant:
                summary["champion"] = participant.get("championName", "?")
                summary["win"] = participant.get("win", False)
                kills = participant.get("kills", 0)
                deaths = participant.get("deaths", 0)
                assists = participant.get("assists", 0)
                summary["kda"] = f"{kills}/{deaths}/{assists}"
                summary["cs"] = participant.get("totalMinionsKilled", 0) + participant.get("neutralMinionsKilled", 0)
                summary["position"] = participant.get("teamPosition", "?")

        return summary

    def get_all_participants_positions(self, timeline, frame_index):
        """Extrai posicoes de todos os participantes em um frame especifico"""
        if not timeline:
            return {}

        frames = timeline.get("info", {}).get("frames", [])
        if frame_index >= len(frames):
            return {}

        frame = frames[frame_index]
        participant_frames = frame.get("participantFrames", {})

        positions = {}
        for pid_str, pdata in participant_frames.items():
            pid = int(pid_str)
            pos = pdata.get("position", {})
            positions[pid] = {
                "x": pos.get("x", 0),
                "y": pos.get("y", 0),
                "level": pdata.get("level", 1),
                "gold": pdata.get("totalGold", 0),
                "cs": pdata.get("minionsKilled", 0) + pdata.get("jungleMinionsKilled", 0),
            }

        return positions

    def is_in_game(self, puuid: str) -> bool:
        """Verifica se o jogador está em uma partida ao vivo (Spectator V5).
        Retorna True se em jogo, False se não (404 = não está em jogo).
        NÃO usa cache — dado em tempo real.
        """
        url  = SPECTATOR_BY_PUUID.format(puuid=puuid)
        data = self.http.get_riot(url)
        return data is not None

    def get_live_game(self, puuid: str) -> dict | None:
        """Retorna dados da partida ao vivo ou None se não estiver em jogo."""
        url = SPECTATOR_BY_PUUID.format(puuid=puuid)
        return self.http.get_riot(url)

    @staticmethod
    def calculate_distance(pos1, pos2):
        """Calcula distancia euclidiana entre duas posicoes no mapa"""
        dx = pos2["x"] - pos1["x"]
        dy = pos2["y"] - pos1["y"]
        return math.sqrt(dx * dx + dy * dy)
