# -*- coding: utf-8 -*-
"""
Wrapper para Riot Live Client Data API (porta 2999)
Disponivel apenas enquanto o jogo esta ativo
"""

import sys
import os

from .config import (
    LIVE_CLIENT_ALLGAMEDATA,
    LIVE_CLIENT_PLAYERLIST,
    LIVE_CLIENT_EVENTS,
    LIVE_CLIENT_GAMESTATS,
    LIVE_CLIENT_ACTIVE_PLAYER,
)

# Logger com fallback
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from logger import get_logger
    logger = get_logger("LiveClient")
except Exception:
    class _DummyLogger:
        def debug(self, msg): pass
        def info(self, msg): print(f"[INFO] {msg}")
        def warning(self, msg): print(f"[WARNING] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
        def exception(self, msg): print(f"[EXCEPTION] {msg}")
    logger = _DummyLogger()


class LiveClientAPI:
    """Wrapper para Riot Live Client Data API (porta 2999)"""

    def __init__(self, http_client):
        self.http = http_client
        self._last_event_id = 0

    def is_available(self):
        """Verifica se a API do cliente esta acessivel (jogo ativo)"""
        data = self.http.get_live(LIVE_CLIENT_GAMESTATS, timeout=1)
        return data is not None

    def get_all_game_data(self):
        """Retorna todos os dados do jogo"""
        return self.http.get_live(LIVE_CLIENT_ALLGAMEDATA)

    def get_player_list(self):
        """Retorna lista de todos os 10 jogadores"""
        return self.http.get_live(LIVE_CLIENT_PLAYERLIST)

    def get_active_player_name(self):
        """Retorna nome do jogador ativo (voce)"""
        return self.http.get_live(LIVE_CLIENT_ACTIVE_PLAYER)

    def get_game_stats(self):
        """Retorna estatisticas do jogo (tempo, modo, mapa)"""
        return self.http.get_live(LIVE_CLIENT_GAMESTATS)

    def get_events(self):
        """Retorna apenas eventos NOVOS desde a ultima chamada"""
        data = self.http.get_live(LIVE_CLIENT_EVENTS)
        if data is None:
            return []

        events = data.get("Events", [])

        # Filtra apenas eventos novos
        new_events = [e for e in events if e.get("EventID", 0) > self._last_event_id]

        if new_events:
            self._last_event_id = max(e.get("EventID", 0) for e in new_events)

        return new_events

    def get_all_events(self):
        """Retorna TODOS os eventos (sem filtro)"""
        data = self.http.get_live(LIVE_CLIENT_EVENTS)
        if data is None:
            return []
        return data.get("Events", [])

    def get_player_by_champion(self, champion_name, players=None):
        """Busca dados de um jogador pelo nome do campeao"""
        if players is None:
            players = self.get_player_list()
        if players is None:
            return None

        for player in players:
            if player.get("championName", "").lower() == champion_name.lower():
                return player
        return None

    def get_player_by_name(self, summoner_name, players=None):
        """Busca dados de um jogador pelo summoner name ou riot id"""
        if players is None:
            players = self.get_player_list()
        if players is None:
            return None

        for player in players:
            if (player.get("summonerName", "") == summoner_name or
                    player.get("riotId", "") == summoner_name):
                return player
        return None

    def identify_jungler(self, team=None, players=None):
        """Identifica o jungler de um time"""
        if players is None:
            players = self.get_player_list()
        if players is None:
            return None

        for player in players:
            # Filtra por time se especificado
            if team and player.get("team", "") != team:
                continue

            # Verifica posicao
            if player.get("position", "").upper() == "JUNGLE":
                return player

            # Fallback: verifica se tem Smite
            spells = player.get("summonerSpells", {})
            for spell_key in ["summonerSpellOne", "summonerSpellTwo"]:
                spell = spells.get(spell_key, {})
                if "Smite" in spell.get("displayName", ""):
                    return player

        return None

    def get_teams(self, players=None):
        """Separa jogadores por time"""
        if players is None:
            players = self.get_player_list()
        if players is None:
            return None, None

        order = [p for p in players if p.get("team") == "ORDER"]
        chaos = [p for p in players if p.get("team") == "CHAOS"]
        return order, chaos

    def get_active_player_team(self, players=None):
        """Descobre em qual time o jogador ativo esta"""
        active_name = self.get_active_player_name()
        if active_name is None:
            return None

        if players is None:
            players = self.get_player_list()
        if players is None:
            return None

        # O active_player_name retorna como string pura (sem JSON)
        # Limpa aspas se houver
        if isinstance(active_name, str):
            active_name = active_name.strip('"')

        for player in players:
            name = player.get("riotId", player.get("summonerName", ""))
            if name == active_name or player.get("summonerName", "") == active_name:
                return player.get("team")

        return None

    def reset_events(self):
        """Reseta o contador de eventos (para nova partida)"""
        self._last_event_id = 0
