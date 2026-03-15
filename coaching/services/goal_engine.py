# -*- coding: utf-8 -*-
"""Motor de metas SMART — verificação de progresso e alertas."""

from datetime import datetime
from typing import List, Tuple

from ..models.goal   import SmartGoal, STATUS_ACTIVE, STATUS_ACHIEVED, STATUS_FAILED
from ..models.player import Player
from .session_manager import save_player


def check_goals(player: Player, current_metrics: dict) -> List[Tuple[SmartGoal, dict]]:
    """
    Verifica o estado de cada meta ativa do jogador.
    Retorna lista de (SmartGoal, progress_dict).
    """
    results = []
    for g_dict in player.goals:
        goal = SmartGoal.from_dict(g_dict)
        if goal.status != STATUS_ACTIVE:
            results.append((goal, {"pct": 0, "achieved": False}))
            continue
        current = current_metrics.get(goal.metric, goal.current_value)
        progress = goal.check_progress(current)
        results.append((goal, progress))
    return results


def update_goal_statuses(player: Player, current_metrics: dict) -> List[str]:
    """
    Atualiza status das metas e persiste. Retorna lista de notificações.
    """
    notifications = []
    updated_goals = []

    for g_dict in player.goals:
        goal = SmartGoal.from_dict(g_dict)

        if goal.status != STATUS_ACTIVE:
            updated_goals.append(goal.to_dict())
            continue

        current = current_metrics.get(goal.metric, goal.current_value)

        if goal.is_achieved(current):
            goal.status      = STATUS_ACHIEVED
            goal.achieved_at = datetime.now().isoformat()
            notifications.append(
                f"✅ Meta atingida: {goal.metric_label} → {current:.2f} (alvo {goal.target_value:.2f})"
            )
        elif goal.days_remaining() < 0:
            goal.status = STATUS_FAILED
            notifications.append(
                f"❌ Meta expirada: {goal.metric_label} — {current:.2f} de {goal.target_value:.2f}"
            )

        updated_goals.append(goal.to_dict())

    player.goals = updated_goals
    save_player(player)
    return notifications


def generate_weekly_alerts(player: Player, current_metrics: dict,
                           prev_metrics: dict) -> List[str]:
    """
    Gera alertas baseados na variação semanal das métricas.
    prev_metrics = métricas da semana passada (baseline recente).
    """
    alerts = []

    thresholds = {
        "cs_per_min":   ("CS/min",          -0.3, False),
        "kda":          ("KDA",             -0.4, False),
        "vision_pm":    ("Visão/min",        -0.15, False),
        "gold_per_min": ("Gold/min",         -20, False),
        "dmg_share":    ("Damage Share",     -0.03, False),
    }

    for metric, (label, threshold, higher_is_worse) in thresholds.items():
        curr = current_metrics.get(metric)
        prev = prev_metrics.get(metric)
        if curr is None or prev is None:
            continue
        delta = curr - prev
        if delta < threshold:
            alerts.append(f"⚠ {label} caiu {abs(delta):.2f} esta semana — reforçar no check-in")

    # Metas próximas do prazo
    for g_dict in player.goals:
        goal = SmartGoal.from_dict(g_dict)
        if goal.status != "active":
            continue
        days = goal.days_remaining()
        if 0 < days <= 7:
            progress = goal.check_progress(current_metrics.get(goal.metric, goal.current_value))
            alerts.append(
                f"⏰ Meta '{goal.metric_label}' vence em {days} dia(s) — "
                f"{progress['pct']:.0f}% concluída"
            )

    return alerts
