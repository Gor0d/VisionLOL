# -*- coding: utf-8 -*-
"""
Diagnóstico inicial de jogador — analisa as últimas N partidas e
identifica pontos fortes/fracos usando o sistema de métricas existente.
"""

from typing import Optional


# Limiares para identificação automática de fraquezas
_WEAKNESS_RULES = [
    ("cs_per_min",   lambda v: v < 7.0,   "Farm abaixo da média (CS/min < 7.0)"),
    ("vision_pm",    lambda v: v < 0.8,   "Controle de visão deficiente (Visão/min < 0.8)"),
    ("kda",          lambda v: v < 2.5,   "Sobrevivência / tomada de decisão (KDA < 2.5)"),
    ("dmg_share",    lambda v: v < 0.22,  "Impacto em teamfights baixo (Damage Share < 22%)"),
    ("kill_part",    lambda v: v < 0.50,  "Baixa participação em kills (< 50%)"),
]


def generate_diagnostic(
    match_api,
    game_name: str,
    tag_line: str,
    role: str,
    count: int = 20,
    queue: Optional[int] = 420,
) -> dict:
    """
    Gera diagnóstico completo do jogador.

    Parâmetros
    ----------
    match_api  : instância de MatchAPI (com http_client configurado)
    game_name  : Riot ID game name
    tag_line   : Riot ID tag line
    role       : posição (TOP/JNG/MID/ADC/SUP)
    count      : número de partidas a analisar
    queue      : 420=Ranked Solo, 400=Normal Draft, None=todas

    Retorna dict com: summoner, role, metrics, champion_pool,
                      top_3_weaknesses, benchmarks
    """
    from riot_api.performance_radar import (
        compute_player_metrics, normalize_metrics, ROLE_BENCHMARKS
    )

    # 1. PUUID
    puuid = match_api.get_puuid(game_name, tag_line)
    if not puuid:
        raise ValueError(f"Jogador '{game_name}#{tag_line}' não encontrado na Riot API.")

    # 2. Match IDs
    match_ids = match_api.get_match_ids(puuid, count=count, queue=queue) or []
    if not match_ids and queue:
        # Fallback: tenta sem filtro de fila
        match_ids = match_api.get_match_ids(puuid, count=count) or []

    # 3. Fetch match data
    match_cache: dict = {}
    summaries = []
    champ_stats: dict = {}  # {champion: {games, wins, kills, deaths, assists}}

    for mid in match_ids:
        md = match_api.get_match_data(mid)
        if not md:
            continue
        match_cache[mid] = md
        summaries.append((mid, {}, md))

        # Coleta dados de campeão
        for p in md.get("info", {}).get("participants", []):
            if p.get("puuid") == puuid:
                champ = p.get("championName", "Unknown")
                won   = p.get("win", False)
                k     = p.get("kills", 0)
                d     = p.get("deaths", 0)
                a     = p.get("assists", 0)
                if champ not in champ_stats:
                    champ_stats[champ] = {"games": 0, "wins": 0, "kills": 0, "deaths": 0, "assists": 0}
                champ_stats[champ]["games"]   += 1
                champ_stats[champ]["wins"]    += int(won)
                champ_stats[champ]["kills"]   += k
                champ_stats[champ]["deaths"]  += d
                champ_stats[champ]["assists"] += a
                break

    # 4. Calcula métricas via sistema existente
    metrics = compute_player_metrics(summaries, match_cache, puuid)

    # 5. Identifica fraquezas
    weaknesses = [msg for metric, fn, msg in _WEAKNESS_RULES if fn(metrics.get(metric, 0))]

    # 6. Champion pool (top 5 por jogos)
    champion_pool = []
    for champ, s in sorted(champ_stats.items(), key=lambda x: -x[1]["games"])[:5]:
        kda = (s["kills"] + s["assists"]) / max(s["deaths"], 1)
        champion_pool.append({
            "name":    champ,
            "games":   s["games"],
            "winrate": s["wins"] / s["games"] * 100 if s["games"] else 0,
            "kda":     round(kda, 2),
        })

    return {
        "game_name":        game_name,
        "tag_line":         tag_line,
        "puuid":            puuid,
        "role":             role,
        "games_analyzed":   len(summaries),
        "metrics":          metrics,
        "norm_metrics":     normalize_metrics(metrics, role),
        "champion_pool":    champion_pool,
        "top_3_weaknesses": weaknesses[:3],
        "benchmarks":       ROLE_BENCHMARKS.get(role, {}),
    }
