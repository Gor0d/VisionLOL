# -*- coding: utf-8 -*-
"""Perfil de jogador/aluno no módulo de coaching."""

from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


ROLES = ("TOP", "JNG", "MID", "ADC", "SUP")
COACHING_TYPES = ("individual", "team")


@dataclass
class Player:
    summoner_name:    str                  # nome de exibição
    game_name:        str                  # Riot ID — gameName
    tag_line:         str                  # Riot ID — tagLine
    role:             str                  # TOP | JNG | MID | ADC | SUP
    rank:             str    = ""          # ex: "Gold II"
    coaching_type:    str    = "individual"
    team_id:          Optional[str] = None
    riot_puuid:       str    = ""
    session_ids:      List[str] = field(default_factory=list)
    goals:            List[dict] = field(default_factory=list)  # SmartGoal.to_dict()
    baseline_metrics: dict       = field(default_factory=dict)  # snapshot ao cadastrar
    notes:            str    = ""
    created_at:       str    = field(default_factory=lambda: datetime.now().isoformat())
    id:               str    = field(default_factory=lambda: str(uuid.uuid4()))

    # ── Serialização ──────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "id":               self.id,
            "summoner_name":    self.summoner_name,
            "game_name":        self.game_name,
            "tag_line":         self.tag_line,
            "role":             self.role,
            "rank":             self.rank,
            "coaching_type":    self.coaching_type,
            "team_id":          self.team_id,
            "riot_puuid":       self.riot_puuid,
            "session_ids":      self.session_ids,
            "goals":            self.goals,
            "baseline_metrics": self.baseline_metrics,
            "notes":            self.notes,
            "created_at":       self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Player":
        return cls(
            id               = d.get("id", str(uuid.uuid4())),
            summoner_name    = d.get("summoner_name", ""),
            game_name        = d.get("game_name", ""),
            tag_line         = d.get("tag_line", "BR1"),
            role             = d.get("role", "MID"),
            rank             = d.get("rank", ""),
            coaching_type    = d.get("coaching_type", "individual"),
            team_id          = d.get("team_id"),
            riot_puuid       = d.get("riot_puuid", ""),
            session_ids      = d.get("session_ids", []),
            goals            = d.get("goals", []),
            baseline_metrics = d.get("baseline_metrics", {}),
            notes            = d.get("notes", ""),
            created_at       = d.get("created_at", datetime.now().isoformat()),
        )

    @property
    def riot_id(self) -> str:
        return f"{self.game_name}#{self.tag_line}"

    @property
    def display(self) -> str:
        return self.summoner_name or self.game_name
