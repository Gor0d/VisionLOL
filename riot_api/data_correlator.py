# -*- coding: utf-8 -*-
"""
Correlaciona dados de atencao (VisionLOL) com eventos do jogo (Riot API)
Gera insights sobre quando o jogador estava distraido durante momentos criticos
"""

import sys
import os
import time

# Logger com fallback
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from logger import get_logger
    logger = get_logger("DataCorrelator")
except Exception:
    class _DummyLogger:
        def debug(self, msg): pass
        def info(self, msg): print(f"[INFO] {msg}")
        def warning(self, msg): print(f"[WARNING] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
        def exception(self, msg): print(f"[EXCEPTION] {msg}")
    logger = _DummyLogger()


class DataCorrelator:
    """Correlaciona dados de atencao com eventos do jogo"""

    def __init__(self):
        self._attention_log = []  # [(game_time, attention_data)]
        self._game_events = []    # [(game_time, event_data)]
        self._correlations = []
        self._insights = []

    def reset(self):
        """Reseta todos os dados para nova partida"""
        self._attention_log = []
        self._game_events = []
        self._correlations = []
        self._insights = []

    def log_attention_state(self, game_time, attention_data):
        """Registra estado de atencao em momento do jogo"""
        self._attention_log.append({
            "game_time": game_time,
            "is_distracted": attention_data.get("is_distracted", False),
            "distraction_type": attention_data.get("distraction_type"),
            "confidence": attention_data.get("confidence", 0),
            "gaze_direction": attention_data.get("gaze_direction"),
        })

    def log_game_event(self, event):
        """Registra evento do jogo"""
        self._game_events.append(event)

    def correlate(self, time_window=10.0):
        """Correlaciona distracao com eventos do jogo"""
        self._correlations = []

        for event in self._game_events:
            event_time = event.get("game_time", 0)

            # Busca estados de atencao na janela de tempo
            attention_states = [
                a for a in self._attention_log
                if abs(a["game_time"] - event_time) <= time_window
            ]

            if not attention_states:
                continue

            # Calcula se estava distraido no momento do evento
            distracted_states = [a for a in attention_states if a["is_distracted"]]
            distraction_ratio = len(distracted_states) / max(len(attention_states), 1)

            was_distracted = distraction_ratio > 0.5

            correlation = {
                "event": event,
                "was_distracted": was_distracted,
                "distraction_ratio": round(distraction_ratio * 100, 1),
                "attention_samples": len(attention_states),
                "distracted_samples": len(distracted_states),
            }

            if was_distracted and distracted_states:
                correlation["distraction_type"] = distracted_states[-1].get("distraction_type")

            self._correlations.append(correlation)

        return self._correlations

    def get_insights(self):
        """Gera insights a partir das correlacoes"""
        if not self._correlations:
            self.correlate()

        self._insights = []

        # Insight 1: Mortes durante distracao
        deaths = [c for c in self._correlations if c["event"].get("type") == "DEATH"]
        distracted_deaths = [c for c in deaths if c["was_distracted"]]

        if deaths:
            if distracted_deaths:
                self._insights.append({
                    "type": "WARNING",
                    "text": f"Voce estava distraido durante {len(distracted_deaths)} de {len(deaths)} mortes",
                    "severity": "high" if len(distracted_deaths) > len(deaths) / 2 else "medium",
                })
            else:
                self._insights.append({
                    "type": "POSITIVE",
                    "text": "Nenhuma morte ocorreu enquanto voce estava distraido!",
                    "severity": "low",
                })

        # Insight 2: Kills perdidos (oportunidades nao aproveitadas)
        ally_kills = [c for c in self._correlations
                      if c["event"].get("type") == "KILL"
                      and c["event"].get("team") == "ORDER"]  # Simplificacao
        distracted_kills = [c for c in ally_kills if c["was_distracted"]]

        if distracted_kills:
            self._insights.append({
                "type": "INFO",
                "text": f"Seu time conseguiu {len(distracted_kills)} kills enquanto voce estava distraido",
                "severity": "low",
            })

        # Insight 3: Tendencia de distracao ao longo do tempo
        if len(self._attention_log) > 100:
            mid = len(self._attention_log) // 2
            first_half = self._attention_log[:mid]
            second_half = self._attention_log[mid:]

            first_dist = sum(1 for a in first_half if a["is_distracted"]) / max(len(first_half), 1)
            second_dist = sum(1 for a in second_half if a["is_distracted"]) / max(len(second_half), 1)

            if second_dist > first_dist * 1.5:
                self._insights.append({
                    "type": "WARNING",
                    "text": "Sua atencao caiu significativamente na segunda metade da partida",
                    "severity": "medium",
                })
            elif second_dist < first_dist * 0.5:
                self._insights.append({
                    "type": "POSITIVE",
                    "text": "Sua atencao melhorou ao longo da partida!",
                    "severity": "low",
                })

        # Insight 4: Eventos criticos ignorados
        critical_events = [
            c for c in self._correlations
            if c["event"].get("type") in ("KILL", "DEATH", "LEVEL_UP")
            and c["event"].get("is_ult_upgrade", False)
            and c["was_distracted"]
        ]

        if critical_events:
            self._insights.append({
                "type": "WARNING",
                "text": f"Voce perdeu {len(critical_events)} momentos criticos (ult upgrades, etc.) por distracao",
                "severity": "high",
            })

        return self._insights

    def get_timeline_data(self):
        """Retorna dados mesclados para visualizacao em timeline"""
        timeline = []

        # Adiciona estados de atencao (amostrados para nao sobrecarregar)
        sample_rate = max(1, len(self._attention_log) // 200)
        for i in range(0, len(self._attention_log), sample_rate):
            a = self._attention_log[i]
            timeline.append({
                "game_time": a["game_time"],
                "type": "attention",
                "is_distracted": a["is_distracted"],
                "confidence": a["confidence"],
            })

        # Adiciona eventos do jogo
        for event in self._game_events:
            timeline.append({
                "game_time": event.get("game_time", 0),
                "type": "game_event",
                "event_type": event.get("type", ""),
                "details": event,
            })

        # Ordena por game_time
        timeline.sort(key=lambda x: x["game_time"])

        return timeline

    def get_distraction_summary(self):
        """Retorna resumo de distracao durante a partida"""
        if not self._attention_log:
            return {"total_samples": 0}

        total = len(self._attention_log)
        distracted = sum(1 for a in self._attention_log if a["is_distracted"])

        return {
            "total_samples": total,
            "distracted_samples": distracted,
            "focused_samples": total - distracted,
            "distraction_pct": round(distracted / total * 100, 1),
            "focus_pct": round((total - distracted) / total * 100, 1),
        }
