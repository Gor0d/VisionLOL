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
        summary = self.get_distraction_summary()

        # ── 0. Resumo geral de foco ─────────────────────────────────────
        if summary["total_samples"] > 0:
            focus_pct = summary["focus_pct"]
            if focus_pct >= 80:
                self._insights.append({
                    "type": "POSITIVE",
                    "text": f"Sessao com {focus_pct}% de foco — otima concentracao!",
                })
            elif focus_pct >= 60:
                self._insights.append({
                    "type": "INFO",
                    "text": f"Foco geral: {focus_pct}% da sessao",
                })
            else:
                self._insights.append({
                    "type": "WARNING",
                    "text": f"Atencao baixa: apenas {focus_pct}% de foco na sessao",
                    "severity": "high",
                })

        # ── 1. Mortes durante distracao ─────────────────────────────────
        deaths = [c for c in self._correlations if c["event"].get("type") == "DEATH"]
        distracted_deaths = [c for c in deaths if c["was_distracted"]]

        if deaths:
            if distracted_deaths:
                self._insights.append({
                    "type": "WARNING",
                    "text": f"Distraido durante {len(distracted_deaths)}/{len(deaths)} mortes",
                    "severity": "high" if len(distracted_deaths) > len(deaths) / 2 else "medium",
                })
            else:
                self._insights.append({
                    "type": "POSITIVE",
                    "text": "Nenhuma morte ocorreu enquanto voce estava distraido!",
                })

        # ── 2. Ult upgrades perdidos ─────────────────────────────────────
        ult_events = [
            c for c in self._correlations
            if c["event"].get("type") == "LEVEL_UP"
            and c["event"].get("is_ult_upgrade")
        ]
        distracted_ults = [c for c in ult_events if c["was_distracted"]]
        if distracted_ults:
            self._insights.append({
                "type": "WARNING",
                "text": f"Distraido durante {len(distracted_ults)} upgrade(s) de ult",
                "severity": "high",
            })

        # ── 3. Objetivos (Dragon / Baron / Rift Herald) ──────────────────
        _OBJ_NAMES = {
            "DragonKill":     "Dragon",
            "BaronKill":      "Baron",
            "RiftHeraldKill": "Rift Herald",
        }
        objectives = [
            c for c in self._correlations
            if c["event"].get("type") == "LIVE_EVENT"
            and c["event"].get("event_name", "") in _OBJ_NAMES
        ]
        distracted_obj = [c for c in objectives if c["was_distracted"]]
        if distracted_obj:
            names = [_OBJ_NAMES[c["event"]["event_name"]] for c in distracted_obj]
            unique = list(dict.fromkeys(names))   # preserva ordem, sem duplicatas
            self._insights.append({
                "type": "WARNING",
                "text": f"Distraido durante {len(distracted_obj)} objetivo(s): {', '.join(unique)}",
                "severity": "high",
            })

        # ── 4. Fase com mais distracao (early/mid/late) ──────────────────
        if len(self._attention_log) > 50:
            def _dist_pct(samples):
                if not samples:
                    return None
                return sum(1 for a in samples if a["is_distracted"]) / len(samples) * 100

            phases = [
                ("Early game (<15 min)", _dist_pct(
                    [a for a in self._attention_log if a["game_time"] < 900])),
                ("Mid game (15-25 min)", _dist_pct(
                    [a for a in self._attention_log if 900 <= a["game_time"] < 1500])),
                ("Late game (>25 min)", _dist_pct(
                    [a for a in self._attention_log if a["game_time"] >= 1500])),
            ]
            valid = [(name, pct) for name, pct in phases if pct is not None]
            if valid:
                worst_name, worst_pct = max(valid, key=lambda x: x[1])
                if worst_pct > 35:
                    self._insights.append({
                        "type": "INFO",
                        "text": f"Mais distraido no {worst_name} ({worst_pct:.0f}% do tempo)",
                    })

        # ── 5. Tendencia de atencao (primeira vs segunda metade) ─────────
        if len(self._attention_log) > 100:
            mid = len(self._attention_log) // 2
            first_dist  = sum(1 for a in self._attention_log[:mid]  if a["is_distracted"]) / mid
            second_dist = sum(1 for a in self._attention_log[mid:]  if a["is_distracted"]) / (len(self._attention_log) - mid)

            if second_dist > first_dist * 1.5:
                self._insights.append({
                    "type": "WARNING",
                    "text": "Atencao caiu na segunda metade da sessao",
                })
            elif second_dist < first_dist * 0.5:
                self._insights.append({
                    "type": "POSITIVE",
                    "text": "Atencao melhorou ao longo da sessao!",
                })

        # ── 6. Maior streak de distracao continua ────────────────────────
        max_streak = current_streak = 0
        for a in self._attention_log:
            if a["is_distracted"]:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0

        streak_sec = max_streak * 0.033   # ~30 fps de amostragem
        if streak_sec > 10:
            self._insights.append({
                "type": "WARNING" if streak_sec > 20 else "INFO",
                "text": f"Maior periodo de distracao continua: {streak_sec:.0f}s",
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
