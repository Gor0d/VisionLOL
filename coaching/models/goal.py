# -*- coding: utf-8 -*-
"""Meta SMART de coaching."""

from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import datetime, date


METRIC_LABELS = {
    "kda":          "KDA",
    "cs_per_min":   "CS/min",
    "vision_pm":    "Visão/min",
    "gold_per_min": "Gold/min",
    "dmg_share":    "Damage Share",
    "kill_part":    "Kill Participation",
}

STATUS_ACTIVE   = "active"
STATUS_ACHIEVED = "achieved"
STATUS_FAILED   = "failed"
STATUS_PAUSED   = "paused"


@dataclass
class SmartGoal:
    player_id:     str
    metric:        str   # chave de METRIC_LABELS
    current_value: float
    target_value:  float
    deadline:      str   # ISO date "YYYY-MM-DD"
    status:        str   = STATUS_ACTIVE
    created_at:    str   = field(default_factory=lambda: datetime.now().isoformat())
    achieved_at:   str   = ""
    id:            str   = field(default_factory=lambda: str(uuid.uuid4()))

    # ── Progresso ─────────────────────────────────────────────────
    def check_progress(self, current: float) -> dict:
        """Retorna progresso atual, % completo e se foi atingida."""
        delta    = current - self.current_value
        needed   = self.target_value - self.current_value
        pct      = (delta / needed * 100) if needed != 0 else 100.0
        achieved = current >= self.target_value if self.target_value > self.current_value \
                   else current <= self.target_value
        return {
            "current":   current,
            "baseline":  self.current_value,
            "target":    self.target_value,
            "delta":     delta,
            "pct":       min(pct, 100.0),
            "achieved":  achieved,
        }

    def is_achieved(self, current: float) -> bool:
        if self.target_value >= self.current_value:
            return current >= self.target_value
        return current <= self.target_value

    def days_remaining(self) -> int:
        try:
            dl = date.fromisoformat(self.deadline[:10])
            return (dl - date.today()).days
        except Exception:
            return 0

    @property
    def metric_label(self) -> str:
        return METRIC_LABELS.get(self.metric, self.metric)

    # ── Serialização ──────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "id":            self.id,
            "player_id":     self.player_id,
            "metric":        self.metric,
            "current_value": self.current_value,
            "target_value":  self.target_value,
            "deadline":      self.deadline,
            "status":        self.status,
            "created_at":    self.created_at,
            "achieved_at":   self.achieved_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SmartGoal":
        return cls(
            id            = d.get("id", str(uuid.uuid4())),
            player_id     = d.get("player_id", ""),
            metric        = d.get("metric", "kda"),
            current_value = float(d.get("current_value", 0)),
            target_value  = float(d.get("target_value", 0)),
            deadline      = d.get("deadline", ""),
            status        = d.get("status", STATUS_ACTIVE),
            created_at    = d.get("created_at", datetime.now().isoformat()),
            achieved_at   = d.get("achieved_at", ""),
        )
