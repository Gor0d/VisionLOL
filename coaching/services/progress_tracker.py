# -*- coding: utf-8 -*-
"""Acompanhamento de evolução do aluno — compara métricas atuais com baseline."""

from typing import List
from .session_manager import list_sessions


def fetch_recent_metrics(match_api, player, recent_count: int = 10) -> dict:
    """
    Calcula métricas das últimas N partidas do jogador.
    Retorna dict {metric: float} — mesmos campos de compute_player_metrics().
    """
    from riot_api.performance_radar import compute_player_metrics

    if not player.riot_puuid:
        return {}

    match_ids = match_api.get_match_ids(player.riot_puuid, count=recent_count) or []
    match_cache = {}
    summaries   = []

    for mid in match_ids:
        md = match_api.get_match_data(mid)
        if md:
            match_cache[mid] = md
            summaries.append((mid, {}, md))

    return compute_player_metrics(summaries, match_cache, player.riot_puuid)


def track_progress(match_api, player, recent_count: int = 10) -> dict:
    """
    Compara métricas atuais com o baseline do cadastro.
    Retorna: { metric: {current, baseline, delta, pct_change} }
    """
    current  = fetch_recent_metrics(match_api, player, recent_count)
    baseline = player.baseline_metrics or {}

    result = {}
    for metric, curr_val in current.items():
        base_val = baseline.get(metric, curr_val)
        delta    = curr_val - base_val
        pct      = (delta / base_val * 100) if base_val else 0
        result[metric] = {
            "current":  round(curr_val, 3),
            "baseline": round(base_val, 3),
            "delta":    round(delta, 3),
            "pct":      round(pct, 1),
        }
    return result


def get_evolution_chart_data(match_api, player, weeks: int = 8) -> dict:
    """
    Retorna série temporal de métricas para plotar gráfico de evolução.
    Divide as partidas dos últimos N weeks em grupos semanais.
    Formato: { "labels": [...], "kda": [...], "cs_per_min": [...], ... }
    """
    from riot_api.performance_radar import compute_player_metrics
    from datetime import datetime, timedelta

    if not player.riot_puuid:
        return {}

    all_ids = match_api.get_match_ids(player.riot_puuid, count=weeks * 10) or []

    # Agrupa por semana: buckets de ~(total / weeks) partidas
    chunk   = max(len(all_ids) // weeks, 1)
    buckets = [all_ids[i:i + chunk] for i in range(0, len(all_ids), chunk)][:weeks]

    labels   = []
    series: dict[str, list] = {}

    for i, bucket in enumerate(reversed(buckets)):
        cache     = {}
        summaries = []
        for mid in bucket:
            md = match_api.get_match_data(mid)
            if md:
                cache[mid] = md
                summaries.append((mid, {}, md))

        if not summaries:
            continue

        metrics = compute_player_metrics(summaries, cache, player.riot_puuid)
        label   = f"S-{len(buckets) - i}"
        labels.append(label)
        for k, v in metrics.items():
            series.setdefault(k, []).append(round(v, 3))

    return {"labels": labels, **series}


def generate_weekly_alerts(match_api, player) -> List[str]:
    """
    Gera alertas comparando métricas recentes (últimas 10) vs. últimas 20 partidas.
    """
    from .goal_engine import generate_weekly_alerts as _gwa

    current  = fetch_recent_metrics(match_api, player, recent_count=10)
    prev     = fetch_recent_metrics(match_api, player, recent_count=20)

    return _gwa(player, current, prev)
