# -*- coding: utf-8 -*-
"""
Analisador de tempo de reacao baseado em dados pos-jogo
- Eficiencia do Flash (usado vs disponivel quando morreu)
- Eficiencia do Zhonya (comprado e usado vs nao)
- Analise de mortes com CC
"""

import sys
import os

# Logger com fallback
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from logger import get_logger
    logger = get_logger("ReactionAnalyzer")
except Exception:
    class _DummyLogger:
        def debug(self, msg): pass
        def info(self, msg): print(f"[INFO] {msg}")
        def warning(self, msg): print(f"[WARNING] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
        def exception(self, msg): print(f"[EXCEPTION] {msg}")
    logger = _DummyLogger()

# Constantes
FLASH_COOLDOWN = 300  # 300 segundos (5 min) sem runa de CDR
FLASH_COOLDOWN_HASTE = 255  # com Cosmic Insight
ZHONYA_ITEM_ID = 2420
STOPWATCH_ITEM_ID = 2420  # Zhonya
GUARDIAN_ANGEL_ITEM_ID = 3026

# Summoner spell IDs
FLASH_SPELL_ID = 4
FLASH_SPELL_NAMES = ["Flash", "SummonerFlash"]

# CC types nos dados de dano recebido
CC_SPELL_TYPES = [
    "STUN", "ROOT", "SNARE", "KNOCK_UP", "KNOCK_BACK",
    "CHARM", "FEAR", "TAUNT", "SUPPRESS", "SLEEP",
    "POLYMORPH", "BLIND", "SILENCE", "GROUND",
]


class ReactionAnalyzer:
    """Analisador de tempo de reacao baseado em dados pos-jogo"""

    def __init__(self, match_api):
        self.match_api = match_api

    def analyze_match_reactions(self, match_id, target_puuid):
        """Analisa tempos de reacao em uma partida concluida"""
        # 1. Busca dados
        match_data = self.match_api.get_match_data(match_id)
        timeline = self.match_api.get_match_timeline(match_id)

        if not match_data or not timeline:
            return None

        # 2. Identifica participante
        target_pid = self.match_api.get_participant_id_by_puuid(match_data, target_puuid)
        participant = self.match_api.get_participant_by_puuid(match_data, target_puuid)

        if not target_pid or not participant:
            logger.error("Jogador nao encontrado na partida")
            return None

        # 3. Extrai dados
        deaths = self._extract_death_events(timeline, target_pid)
        flash_analysis = self._analyze_flash_efficiency(participant, deaths, timeline, target_pid)
        zhonya_analysis = self._analyze_zhonya_efficiency(participant, deaths, timeline, target_pid)
        cc_analysis = self._analyze_cc_deaths(deaths, timeline)
        death_breakdown = self._build_death_breakdown(deaths, match_data, timeline)

        return {
            "match_id": match_id,
            "champion": participant.get("championName", "?"),
            "position": participant.get("teamPosition", "?"),
            "total_deaths": participant.get("deaths", 0),
            "total_kills": participant.get("kills", 0),
            "total_assists": participant.get("assists", 0),
            "flash_analysis": flash_analysis,
            "zhonya_analysis": zhonya_analysis,
            "cc_analysis": cc_analysis,
            "death_breakdown": death_breakdown,
            "game_duration_min": match_data.get("info", {}).get("gameDuration", 0) // 60,
        }

    def _extract_death_events(self, timeline, target_pid):
        """Extrai todos os eventos de morte do jogador alvo"""
        deaths = []
        frames = timeline.get("info", {}).get("frames", [])

        for frame in frames:
            for event in frame.get("events", []):
                if event.get("type") == "CHAMPION_KILL" and event.get("victimId") == target_pid:
                    deaths.append({
                        "timestamp_ms": event.get("timestamp", 0),
                        "minute": event.get("timestamp", 0) // 60000,
                        "killer_id": event.get("killerId", 0),
                        "assisters": event.get("assistingParticipantIds", []),
                        "position": event.get("position", {}),
                        "victim_damage": event.get("victimDamageReceived", []),
                        "victim_damage_dealt": event.get("victimDamageDealt", []),
                    })

        logger.info(f"Encontradas {len(deaths)} mortes do jogador alvo")
        return deaths

    def _analyze_flash_efficiency(self, participant, deaths, timeline, target_pid):
        """Analisa eficiencia do uso de Flash"""
        # Verifica se o jogador tem Flash
        summoner1 = participant.get("summoner1Id", 0)
        summoner2 = participant.get("summoner2Id", 0)
        has_flash = FLASH_SPELL_ID in (summoner1, summoner2)

        if not has_flash:
            return {
                "has_flash": False,
                "message": "Flash nao equipado nesta partida",
            }

        flash_slot = 1 if summoner1 == FLASH_SPELL_ID else 2
        flash_casts = participant.get(f"summoner{flash_slot}Casts", 0)

        # Analisa mortes em relacao ao Flash
        # Heuristica: se morreu muitas vezes com poucos usos de Flash = ineficiente
        total_deaths = participant.get("deaths", 0)
        game_duration = participant.get("timePlayed", 0)  # segundos

        # Flash maximo possivel = duracao / cooldown
        max_flash_uses = game_duration // FLASH_COOLDOWN if game_duration > 0 else 0

        # Taxa de uso
        flash_usage_rate = flash_casts / max(max_flash_uses, 1) * 100

        # Mortes por Flash disponivel (heuristica)
        # Se morreu mais vezes do que usou Flash, provavelmente nao usou em algumas mortes
        deaths_without_flash_estimate = max(0, total_deaths - flash_casts)

        return {
            "has_flash": True,
            "flash_casts": flash_casts,
            "total_deaths": total_deaths,
            "max_possible_uses": max_flash_uses,
            "usage_rate_pct": round(flash_usage_rate, 1),
            "deaths_without_flash_estimate": deaths_without_flash_estimate,
            "efficiency": self._rate_flash_efficiency(flash_casts, total_deaths, max_flash_uses),
        }

    def _rate_flash_efficiency(self, casts, deaths, max_uses):
        """Classifica eficiencia do Flash"""
        if deaths == 0:
            return "EXCELENTE"

        ratio = casts / max(deaths, 1)

        if ratio >= 0.8:
            return "BOM"
        elif ratio >= 0.5:
            return "REGULAR"
        else:
            return "PRECISA MELHORAR"

    def _analyze_zhonya_efficiency(self, participant, deaths, timeline, target_pid):
        """Analisa eficiencia do Zhonya's Hourglass"""
        # Verifica se comprou Zhonya
        items = []
        for i in range(7):
            item_id = participant.get(f"item{i}", 0)
            if item_id > 0:
                items.append(item_id)

        has_zhonya = ZHONYA_ITEM_ID in items

        if not has_zhonya:
            return {
                "has_zhonya": False,
                "message": "Zhonya nao comprado nesta partida",
            }

        # Encontra quando Zhonya foi comprado
        zhonya_purchase_time = None
        frames = timeline.get("info", {}).get("frames", [])
        for frame in frames:
            for event in frame.get("events", []):
                if (event.get("type") == "ITEM_PURCHASED"
                        and event.get("participantId") == target_pid
                        and event.get("itemId") == ZHONYA_ITEM_ID):
                    zhonya_purchase_time = event.get("timestamp", 0)
                    break
            if zhonya_purchase_time is not None:
                break

        # Mortes apos comprar Zhonya
        if zhonya_purchase_time is not None:
            deaths_after_zhonya = [
                d for d in deaths if d["timestamp_ms"] > zhonya_purchase_time
            ]
        else:
            deaths_after_zhonya = deaths

        return {
            "has_zhonya": True,
            "purchase_minute": zhonya_purchase_time // 60000 if zhonya_purchase_time else None,
            "deaths_after_purchase": len(deaths_after_zhonya),
            "total_deaths": len(deaths),
        }

    def _analyze_cc_deaths(self, deaths, timeline):
        """Analisa mortes envolvendo CC"""
        cc_deaths = 0
        total_cc_sources = 0

        for death in deaths:
            has_cc = False
            damage_received = death.get("victim_damage", [])

            for dmg in damage_received:
                spell_name = dmg.get("spellName", "")
                # Heuristica: muitos spells de CC tem nomes conhecidos
                # A API nao marca explicitamente "CC type" no victimDamageReceived,
                # mas podemos inferir pelo spell name e se foi ability vs basic
                if dmg.get("basic") is False and dmg.get("spellSlot", -1) >= 0:
                    # Habilidade — possivelmente CC
                    has_cc = True
                    total_cc_sources += 1

            if has_cc:
                cc_deaths += 1

        return {
            "total_deaths": len(deaths),
            "deaths_with_abilities": cc_deaths,
            "ability_death_pct": round(cc_deaths / max(len(deaths), 1) * 100, 1),
            "avg_damage_sources_per_death": round(
                sum(len(d.get("victim_damage", [])) for d in deaths) / max(len(deaths), 1), 1
            ),
        }

    def _build_death_breakdown(self, deaths, match_data, timeline):
        """Constroi breakdown detalhado de cada morte"""
        participants = match_data.get("info", {}).get("participants", [])
        pid_to_champ = {}
        for p in participants:
            pid_to_champ[p.get("participantId")] = p.get("championName", "?")

        breakdown = []
        for i, death in enumerate(deaths):
            minute = death["minute"]
            killer = pid_to_champ.get(death["killer_id"], "?")
            assisters = [pid_to_champ.get(a, "?") for a in death["assisters"]]
            num_enemies = 1 + len(assisters)

            # Analisa se foi solo kill ou gank
            if num_enemies >= 3:
                context = "TEAMFIGHT"
            elif num_enemies == 2:
                context = "GANK (2v1)"
            else:
                context = "SOLO KILL"

            breakdown.append({
                "death_number": i + 1,
                "minute": minute,
                "killer": killer,
                "assisters": assisters,
                "num_enemies": num_enemies,
                "context": context,
                "position": death["position"],
            })

        return breakdown

    def format_report(self, report):
        """Formata relatorio de reacao como texto legivel"""
        if not report:
            return "Sem dados para analisar"

        lines = []
        lines.append("=" * 50)
        lines.append("ANALISE DE REACAO")
        lines.append("=" * 50)
        lines.append(f"Campeao: {report['champion']} ({report['position']})")
        lines.append(f"KDA: {report['total_kills']}/{report['total_deaths']}/{report['total_assists']}")
        lines.append(f"Duracao: {report['game_duration_min']} min")
        lines.append("")

        # Flash
        flash = report["flash_analysis"]
        lines.append("--- FLASH ---")
        if flash.get("has_flash"):
            lines.append(f"Usos: {flash['flash_casts']}")
            lines.append(f"Usos maximos possiveis: {flash['max_possible_uses']}")
            lines.append(f"Taxa de uso: {flash['usage_rate_pct']}%")
            lines.append(f"Mortes sem Flash (estimativa): {flash['deaths_without_flash_estimate']}")
            lines.append(f"Avaliacao: {flash['efficiency']}")
        else:
            lines.append(flash["message"])
        lines.append("")

        # Zhonya
        zhonya = report["zhonya_analysis"]
        lines.append("--- ZHONYA ---")
        if zhonya.get("has_zhonya"):
            lines.append(f"Comprado no minuto: {zhonya['purchase_minute']}")
            lines.append(f"Mortes apos compra: {zhonya['deaths_after_purchase']}")
        else:
            lines.append(zhonya["message"])
        lines.append("")

        # CC
        cc = report["cc_analysis"]
        lines.append("--- MORTES COM HABILIDADES ---")
        lines.append(f"Mortes por habilidades: {cc['deaths_with_abilities']}/{cc['total_deaths']} ({cc['ability_death_pct']}%)")
        lines.append(f"Media de fontes de dano por morte: {cc['avg_damage_sources_per_death']}")
        lines.append("")

        # Breakdown
        lines.append("--- DETALHAMENTO POR MORTE ---")
        for d in report["death_breakdown"]:
            assisters_str = f" + {', '.join(d['assisters'])}" if d["assisters"] else ""
            lines.append(f"  #{d['death_number']} Min {d['minute']}: {d['killer']}{assisters_str} [{d['context']}]")

        lines.append("=" * 50)
        return "\n".join(lines)
