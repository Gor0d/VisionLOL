# -*- coding: utf-8 -*-
"""Sessão de coaching — registro completo de um encontro coach-aluno."""

from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class CoachingSession:
    player_id:         str
    date:              str   = field(default_factory=lambda: datetime.now().isoformat())
    duration_minutes:  int   = 60
    # 1 — CHECK-IN
    checkin_notes:     str   = ""
    checkin_mood:      int   = 3     # 1-5
    # 2 — ANÁLISE DE REPLAY
    replay_game_id:    str   = ""
    replay_notes:      str   = ""
    key_mistakes:      List[str] = field(default_factory=list)   # máx 3
    # 3 — PRÁTICA GUIADA
    drill_performed:   str   = ""
    # 4 — DEBRIEF + HOMEWORK
    homework:          List[str] = field(default_factory=list)   # máx 5
    coach_rating:      int   = 3     # 1-5
    next_session_date: str   = ""
    # Snapshot de métricas no dia da sessão
    metrics_snapshot:  dict  = field(default_factory=dict)
    id:                str   = field(default_factory=lambda: str(uuid.uuid4()))

    # ── Serialização ──────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "id":                self.id,
            "player_id":         self.player_id,
            "date":              self.date,
            "duration_minutes":  self.duration_minutes,
            "checkin_notes":     self.checkin_notes,
            "checkin_mood":      self.checkin_mood,
            "replay_game_id":    self.replay_game_id,
            "replay_notes":      self.replay_notes,
            "key_mistakes":      self.key_mistakes,
            "drill_performed":   self.drill_performed,
            "homework":          self.homework,
            "coach_rating":      self.coach_rating,
            "next_session_date": self.next_session_date,
            "metrics_snapshot":  self.metrics_snapshot,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CoachingSession":
        return cls(
            id                = d.get("id", str(uuid.uuid4())),
            player_id         = d.get("player_id", ""),
            date              = d.get("date", datetime.now().isoformat()),
            duration_minutes  = d.get("duration_minutes", 60),
            checkin_notes     = d.get("checkin_notes", ""),
            checkin_mood      = d.get("checkin_mood", 3),
            replay_game_id    = d.get("replay_game_id", ""),
            replay_notes      = d.get("replay_notes", ""),
            key_mistakes      = d.get("key_mistakes", []),
            drill_performed   = d.get("drill_performed", ""),
            homework          = d.get("homework", []),
            coach_rating      = d.get("coach_rating", 3),
            next_session_date = d.get("next_session_date", ""),
            metrics_snapshot  = d.get("metrics_snapshot", {}),
        )

    def generate_summary(self) -> str:
        date_str = self.date[:10]
        mood_str = "⭐" * self.checkin_mood
        hw_str   = "\n".join(f"  • {h}" for h in self.homework) or "  (sem tarefas)"
        mistakes = "\n".join(f"  {i+1}. {m}" for i, m in enumerate(self.key_mistakes)) or "  (não registrado)"
        return (
            f"Sessão {date_str} — {self.duration_minutes}min | Humor: {mood_str}\n"
            f"Check-in: {self.checkin_notes or '—'}\n"
            f"Erros identificados:\n{mistakes}\n"
            f"Drill: {self.drill_performed or '—'}\n"
            f"Homework:\n{hw_str}"
        )
