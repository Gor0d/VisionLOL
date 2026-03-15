# -*- coding: utf-8 -*-
"""Persistência de jogadores e sessões em JSON (coaching_data/)."""

import json
import os
from datetime import datetime
from typing import List, Optional

from ..models.player  import Player
from ..models.session import CoachingSession

# ── Paths ──────────────────────────────────────────────────────────────
_ROOT         = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "coaching_data")
_PLAYERS_FILE = os.path.join(_ROOT, "players.json")
_SESSIONS_DIR = os.path.join(_ROOT, "sessions")


def _ensure_dirs():
    os.makedirs(_SESSIONS_DIR, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════
#  PLAYERS
# ══════════════════════════════════════════════════════════════════════

def load_players() -> List[Player]:
    _ensure_dirs()
    if not os.path.exists(_PLAYERS_FILE):
        return []
    try:
        with open(_PLAYERS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return [Player.from_dict(d) for d in data]
    except Exception:
        return []


def save_players(players: List[Player]):
    _ensure_dirs()
    with open(_PLAYERS_FILE, "w", encoding="utf-8") as f:
        json.dump([p.to_dict() for p in players], f, ensure_ascii=False, indent=2)


def save_player(player: Player):
    players = load_players()
    idx = next((i for i, p in enumerate(players) if p.id == player.id), None)
    if idx is None:
        players.append(player)
    else:
        players[idx] = player
    save_players(players)


def load_player(player_id: str) -> Optional[Player]:
    return next((p for p in load_players() if p.id == player_id), None)


def delete_player(player_id: str):
    players = [p for p in load_players() if p.id != player_id]
    save_players(players)


# ══════════════════════════════════════════════════════════════════════
#  SESSIONS
# ══════════════════════════════════════════════════════════════════════

def save_session(session: CoachingSession):
    _ensure_dirs()
    path = os.path.join(_SESSIONS_DIR, f"{session.id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)

    # Atualiza session_ids no player
    player = load_player(session.player_id)
    if player and session.id not in player.session_ids:
        player.session_ids.append(session.id)
        save_player(player)


def load_session(session_id: str) -> Optional[CoachingSession]:
    path = os.path.join(_SESSIONS_DIR, f"{session_id}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return CoachingSession.from_dict(json.load(f))
    except Exception:
        return None


def list_sessions(player_id: str) -> List[CoachingSession]:
    player = load_player(player_id)
    if not player:
        return []
    sessions = []
    for sid in player.session_ids:
        s = load_session(sid)
        if s:
            sessions.append(s)
    return sorted(sessions, key=lambda s: s.date, reverse=True)


def delete_session(session_id: str):
    path = os.path.join(_SESSIONS_DIR, f"{session_id}.json")
    if os.path.exists(path):
        os.remove(path)
    # Remove do player
    for player in load_players():
        if session_id in player.session_ids:
            player.session_ids.remove(session_id)
            save_player(player)
            break


def get_upcoming_sessions(days_ahead: int = 7) -> List[dict]:
    """Retorna sessões agendadas nos próximos N dias."""
    from datetime import date, timedelta
    cutoff = (date.today() + timedelta(days=days_ahead)).isoformat()
    today  = date.today().isoformat()
    result = []
    for player in load_players():
        for sid in player.session_ids:
            s = load_session(sid)
            if s and s.next_session_date and today <= s.next_session_date[:10] <= cutoff:
                result.append({
                    "player":  player,
                    "session": s,
                    "date":    s.next_session_date[:10],
                })
    return sorted(result, key=lambda x: x["date"])
