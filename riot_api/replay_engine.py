# -*- coding: utf-8 -*-
"""
ReplayEngine - Pre-processa Match-V5 Timeline para replay animado.
Queries O(1)/O(log n) para posicoes, wards, eventos, teamfights.
"""

import sys
import os
import math
import bisect

# Logger com fallback
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from logger import get_logger
    logger = get_logger("ReplayEngine")
except Exception:
    class _DummyLogger:
        def debug(self, msg): pass
        def info(self, msg): print(f"[INFO] {msg}")
        def warning(self, msg): print(f"[WARNING] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
    logger = _DummyLogger()

# Constantes do mapa
MAP_MAX_X = 14820
MAP_MAX_Y = 14881

# Duracoes de wards (ms)
WARD_DURATIONS = {
    "SIGHT_WARD": 90_000,
    "YELLOW_TRINKET": 90_000,
    "BLUE_TRINKET": 60_000,
    "CONTROL_WARD": None,       # Ate ser destruida
    "UNDEFINED": 90_000,
}

# Teamfight detection
TF_TIME_WINDOW_MS = 15_000
TF_DISTANCE_THRESHOLD = 3000
TF_MIN_KILLS = 3


class ReplayEngine:
    """Pre-processa timeline para replay animado a 30fps."""

    def __init__(self, timeline, match_data, target_puuid):
        self.pid_map = {}           # {pid: {champion, position, team_id}}
        self.target_pid = None
        self.target_team = None
        self.game_duration_ms = 0

        # Pre-processados
        self._frames = []           # [{timestamp_ms, positions: {pid: (x,y)}, stats: {pid: {...}}}]
        self._kills = []            # [{timestamp_ms, x, y, killer_pid, victim_pid, assisters}]
        self._objectives = []       # [{timestamp_ms, x, y, monster_type, sub_type, killer_team, killer_pid}]
        self._buildings = []        # [{timestamp_ms, x, y, building_type, killer_team}]
        self._ward_lifetimes = []   # [{id, start_ms, end_ms, x, y, ward_type, team_id, creator_pid}]
        self._teamfights = []       # [{start_ms, end_ms, center_x, center_y, kill_count}]

        # Novos: detalhes profissionais
        self._level_ups = []        # [{timestamp_ms, pid, level}]
        self._skill_ups = []        # [{timestamp_ms, pid, skill_slot, skill_name}]
        self._special_kills = []    # [{timestamp_ms, x, y, kill_type, killer_pid}]
        self._recalls = []          # [{timestamp_ms, pid, end_ms}]
        self._item_purchases = []   # [{timestamp_ms, pid, item_id}]
        self._death_timers = {}     # {pid: [(death_ms, respawn_ms)]}
        self._tower_states = {}     # {(team, lane, type): {"alive": bool, "destroyed_ms": int, "x": x, "y": y}}

        # Posicoes das bases (fountain) por time
        self._base_positions = {100: (600, 450), 200: (14200, 14200)}

        # KDA tracking por minuto
        self._kda_by_frame = {}     # {frame_idx: {pid: {kills, deaths, assists}}}

        self._preprocess(timeline, match_data, target_puuid)

    # ===================================================================
    #  PRE-PROCESSAMENTO (executado uma vez no __init__)
    # ===================================================================

    def _preprocess(self, timeline, match_data, target_puuid):
        """Extrai e indexa todos os dados da timeline."""
        participants = match_data.get("info", {}).get("participants", [])
        frames = timeline.get("info", {}).get("frames", [])

        # Duracao
        self.game_duration_ms = match_data.get("info", {}).get("gameDuration", 0) * 1000

        # Mapa de participantes
        for p in participants:
            pid = p.get("participantId")
            self.pid_map[pid] = {
                "champion": p.get("championName", "?"),
                "position": p.get("teamPosition", "?"),
                "team_id": p.get("teamId", 100),
                "summoner": p.get("riotIdGameName", p.get("summonerName", "?")),
            }
            if p.get("puuid") == target_puuid:
                self.target_pid = pid
                self.target_team = p.get("teamId", 100)

        # Extrai frames (posicoes + stats)
        for frame in frames:
            ts = frame.get("timestamp", 0)
            positions = {}
            stats = {}
            pframes = frame.get("participantFrames", {})

            for pid_str, pf in pframes.items():
                pid = int(pid_str)
                pos = pf.get("position", {})
                x, y = pos.get("x", 0), pos.get("y", 0)
                positions[pid] = (x, y)
                stats[pid] = {
                    "level": pf.get("level", 1),
                    "gold": pf.get("totalGold", 0),
                    "cs": pf.get("minionsKilled", 0) + pf.get("jungleMinionsKilled", 0),
                }

            self._frames.append({
                "timestamp_ms": ts,
                "positions": positions,
                "stats": stats,
            })

        # Extrai eventos e wards
        raw_wards_placed = []
        raw_wards_killed = []
        kill_accumulator = {}  # {pid: {kills, deaths, assists}} acumulativo

        for pid in self.pid_map:
            kill_accumulator[pid] = {"kills": 0, "deaths": 0, "assists": 0}

        for frame_idx, frame in enumerate(frames):
            for event in frame.get("events", []):
                etype = event.get("type")
                ts = event.get("timestamp", 0)

                if etype == "CHAMPION_KILL":
                    pos = event.get("position", {})
                    killer = event.get("killerId", 0)
                    victim = event.get("victimId", 0)
                    assisters = event.get("assistingParticipantIds", [])
                    self._kills.append({
                        "timestamp_ms": ts,
                        "x": pos.get("x", 0),
                        "y": pos.get("y", 0),
                        "killer_pid": killer,
                        "victim_pid": victim,
                        "assisters": assisters,
                    })
                    # Acumula KDA
                    if killer in kill_accumulator:
                        kill_accumulator[killer]["kills"] += 1
                    if victim in kill_accumulator:
                        kill_accumulator[victim]["deaths"] += 1
                    for a in assisters:
                        if a in kill_accumulator:
                            kill_accumulator[a]["assists"] += 1

                elif etype == "ELITE_MONSTER_KILL":
                    pos = event.get("position", {})
                    self._objectives.append({
                        "timestamp_ms": ts,
                        "x": pos.get("x", 0),
                        "y": pos.get("y", 0),
                        "monster_type": event.get("monsterType", ""),
                        "sub_type": event.get("monsterSubType", ""),
                        "killer_team": event.get("killerTeamId", 0),
                        "killer_pid": event.get("killerId", 0),
                    })

                elif etype == "BUILDING_KILL":
                    pos = event.get("position", {})
                    self._buildings.append({
                        "timestamp_ms": ts,
                        "x": pos.get("x", 0),
                        "y": pos.get("y", 0),
                        "building_type": event.get("buildingType", ""),
                        "tower_type": event.get("towerType", ""),
                        "lane_type": event.get("laneType", ""),
                        "killer_team": event.get("teamId", 0),
                    })

                elif etype == "WARD_PLACED":
                    creator = event.get("creatorId", 0)
                    raw_wards_placed.append({
                        "timestamp_ms": ts,
                        "creator_pid": creator,
                        "ward_type": event.get("wardType", "UNDEFINED"),
                        "team_id": self.pid_map.get(creator, {}).get("team_id", 0),
                    })

                elif etype == "WARD_KILL":
                    raw_wards_killed.append({
                        "timestamp_ms": ts,
                        "killer_pid": event.get("killerId", 0),
                        "ward_type": event.get("wardType", "UNDEFINED"),
                    })

                elif etype == "LEVEL_UP":
                    pid_val = event.get("participantId", 0)
                    if pid_val > 0 and ts > 0:
                        self._level_ups.append({
                            "timestamp_ms": ts,
                            "pid": pid_val,
                            "level": event.get("level", 0),
                        })

                elif etype == "SKILL_LEVEL_UP":
                    pid_val = event.get("participantId", 0)
                    if pid_val > 0 and ts > 0:
                        slot = event.get("skillSlot", 0)
                        self._skill_ups.append({
                            "timestamp_ms": ts,
                            "pid": pid_val,
                            "skill_slot": slot,
                            "skill_name": {1: "Q", 2: "W", 3: "E", 4: "R"}.get(slot, "?"),
                        })

                elif etype == "CHAMPION_SPECIAL_KILL":
                    pos = event.get("position", {})
                    self._special_kills.append({
                        "timestamp_ms": ts,
                        "x": pos.get("x", 0),
                        "y": pos.get("y", 0),
                        "kill_type": event.get("killType", ""),
                        "killer_pid": event.get("killerId", 0),
                    })

                elif etype == "ITEM_PURCHASED":
                    self._item_purchases.append({
                        "timestamp_ms": ts,
                        "pid": event.get("participantId", 0),
                        "item_id": event.get("itemId", 0),
                    })

            # Snapshot KDA no final de cada frame
            self._kda_by_frame[frame_idx] = {
                pid: dict(kda) for pid, kda in kill_accumulator.items()
            }

        # Ordena eventos por timestamp
        self._kills.sort(key=lambda e: e["timestamp_ms"])
        self._objectives.sort(key=lambda e: e["timestamp_ms"])
        self._buildings.sort(key=lambda e: e["timestamp_ms"])
        self._level_ups.sort(key=lambda e: e["timestamp_ms"])
        self._skill_ups.sort(key=lambda e: e["timestamp_ms"])
        self._special_kills.sort(key=lambda e: e["timestamp_ms"])
        self._item_purchases.sort(key=lambda e: e["timestamp_ms"])

        # Constroi ward lifetimes
        self._build_ward_lifetimes(raw_wards_placed, raw_wards_killed)

        # Detecta teamfights
        self._detect_teamfights()

        # Constroi tower states (posicoes reais dos BUILDING_KILL)
        self._build_tower_states()

        # Detecta recalls
        self._detect_recalls()

        # Calcula death timers reais
        self._build_death_timers()

        # Detecta base positions do frame 0
        if self._frames:
            f0_pos = self._frames[0]["positions"]
            blue_pids = [pid for pid, info in self.pid_map.items() if info["team_id"] == 100]
            red_pids = [pid for pid, info in self.pid_map.items() if info["team_id"] == 200]
            if blue_pids:
                bx = sum(f0_pos.get(p, (600, 450))[0] for p in blue_pids) // len(blue_pids)
                by = sum(f0_pos.get(p, (600, 450))[1] for p in blue_pids) // len(blue_pids)
                self._base_positions[100] = (bx, by)
            if red_pids:
                rx = sum(f0_pos.get(p, (14200, 14200))[0] for p in red_pids) // len(red_pids)
                ry = sum(f0_pos.get(p, (14200, 14200))[1] for p in red_pids) // len(red_pids)
                self._base_positions[200] = (rx, ry)

        logger.info(
            f"ReplayEngine: {len(self._frames)} frames, "
            f"{len(self._kills)} kills, {len(self._objectives)} obj, "
            f"{len(self._ward_lifetimes)} wards, {len(self._teamfights)} teamfights, "
            f"{len(self._recalls)} recalls, {len(self._tower_states)} towers, "
            f"duration {self.game_duration_ms // 1000}s"
        )

    # Distancia maxima por intervalo de 60s sem ser teleporte/recall
    # (~400 units/s * 60s = 24000 max, mas deslocamento tipico é <4000)
    _TELEPORT_THRESHOLD = 5_000

    def _interpolate_position(self, pid, timestamp_ms):
        """Estima posicao de um jogador entre frames.

        Se a distância entre dois frames consecutivos supera _TELEPORT_THRESHOLD
        (recall / tp / morte+respawn), evita a interpolação linear que faria o
        ícone deslizar pelo mapa: usa a posição do frame mais próximo no tempo.
        """
        if not self._frames:
            return None, None

        minute_f = timestamp_ms / 60000.0
        idx_before = int(minute_f)
        idx_after = idx_before + 1

        idx_before = max(0, min(idx_before, len(self._frames) - 1))
        idx_after = max(0, min(idx_after, len(self._frames) - 1))

        pos_before = self._frames[idx_before]["positions"].get(pid, (0, 0))
        x1, y1 = pos_before

        if x1 == 0 and y1 == 0:
            return None, None

        if idx_before == idx_after:
            return x1, y1

        pos_after = self._frames[idx_after]["positions"].get(pid, (0, 0))
        x2, y2 = pos_after

        if x2 == 0 and y2 == 0:
            return x1, y1

        t = minute_f - idx_before

        # Detecta salto grande (teleporte / recall / morte+respawn)
        dist = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        if dist > self._TELEPORT_THRESHOLD:
            # Exibe posição do frame mais próximo no tempo (sem deslize)
            return (x1, y1) if t < 0.5 else (x2, y2)

        return int(x1 + (x2 - x1) * t), int(y1 + (y2 - y1) * t)

    def _build_ward_lifetimes(self, placed, killed):
        """Constroi lifecycle de cada ward (start → end)."""
        ward_id = 0
        # Indexa kills por ward_type para matching rapido
        kills_by_type = {}
        for wk in killed:
            wt = wk["ward_type"]
            if wt not in kills_by_type:
                kills_by_type[wt] = []
            kills_by_type[wt].append(wk)

        # Marca quais kills ja foram matched
        matched_kills = set()

        for wp in placed:
            ts = wp["timestamp_ms"]
            wtype = wp["ward_type"]
            creator = wp["creator_pid"]
            team = wp["team_id"]

            # Estima posicao
            ix, iy = self._interpolate_position(creator, ts)
            if ix is None:
                continue

            # Determina end_ms
            duration = WARD_DURATIONS.get(wtype, 90_000)
            if duration is None:
                # Control ward — dura ate ser killed ou fim do jogo
                end_ms = self.game_duration_ms
            else:
                end_ms = ts + duration

            # Tenta casar com um WARD_KILL
            potential_kills = kills_by_type.get(wtype, [])
            for i, wk in enumerate(potential_kills):
                if id(wk) in matched_kills:
                    continue
                if wk["timestamp_ms"] < ts:
                    continue
                if wk["timestamp_ms"] > end_ms + 5000:
                    break
                # Match! Ward foi destruida nesse momento
                end_ms = wk["timestamp_ms"]
                matched_kills.add(id(wk))
                break

            # Clamp ao fim do jogo
            end_ms = min(end_ms, self.game_duration_ms)

            self._ward_lifetimes.append({
                "id": ward_id,
                "start_ms": ts,
                "end_ms": end_ms,
                "x": ix,
                "y": iy,
                "ward_type": wtype,
                "team_id": team,
                "creator_pid": creator,
            })
            ward_id += 1

        # Ordena por start_ms para busca eficiente
        self._ward_lifetimes.sort(key=lambda w: w["start_ms"])

    def _detect_teamfights(self):
        """Detecta teamfights como clusters de kills proximos no tempo e espaco."""
        if len(self._kills) < TF_MIN_KILLS:
            return

        kills = self._kills
        used = [False] * len(kills)

        for i in range(len(kills)):
            if used[i]:
                continue

            cluster = [i]
            used[i] = True

            # Expande cluster
            for j in range(i + 1, len(kills)):
                if used[j]:
                    continue
                if kills[j]["timestamp_ms"] - kills[cluster[-1]]["timestamp_ms"] > TF_TIME_WINDOW_MS:
                    break

                # Verifica distancia com qualquer kill do cluster
                close = False
                for ci in cluster:
                    dx = kills[j]["x"] - kills[ci]["x"]
                    dy = kills[j]["y"] - kills[ci]["y"]
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist < TF_DISTANCE_THRESHOLD:
                        close = True
                        break

                if close:
                    cluster.append(j)
                    used[j] = True

            if len(cluster) >= TF_MIN_KILLS:
                cluster_kills = [kills[c] for c in cluster]
                start_ms = cluster_kills[0]["timestamp_ms"]
                end_ms = cluster_kills[-1]["timestamp_ms"]
                cx = int(sum(k["x"] for k in cluster_kills) / len(cluster_kills))
                cy = int(sum(k["y"] for k in cluster_kills) / len(cluster_kills))

                self._teamfights.append({
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "center_x": cx,
                    "center_y": cy,
                    "kill_count": len(cluster_kills),
                })

    # Known Summoner's Rift tower positions (game coordinates)
    _TOWER_POSITIONS = {
        # Blue team (100)
        (100, "TOP", "OUTER"): (981, 10441),
        (100, "TOP", "INNER"): (1512, 6699),
        (100, "TOP", "BASE"): (1169, 4287),
        (100, "MID", "OUTER"): (5846, 6396),
        (100, "MID", "INNER"): (5048, 4812),
        (100, "MID", "BASE"): (3651, 3696),
        (100, "BOT", "OUTER"): (10504, 1029),
        (100, "BOT", "INNER"): (6919, 1483),
        (100, "BOT", "BASE"): (4281, 1253),
        (100, "MID", "NEXUS_1"): (1748, 2270),
        (100, "MID", "NEXUS_2"): (2177, 1807),
        # Red team (200)
        (200, "TOP", "OUTER"): (4318, 13875),
        (200, "TOP", "INNER"): (7943, 13411),
        (200, "TOP", "BASE"): (10481, 13650),
        (200, "MID", "OUTER"): (8955, 8510),
        (200, "MID", "INNER"): (9767, 10113),
        (200, "MID", "BASE"): (11134, 11207),
        (200, "BOT", "OUTER"): (13866, 4505),
        (200, "BOT", "INNER"): (13327, 8226),
        (200, "BOT", "BASE"): (13624, 10572),
        (200, "MID", "NEXUS_1"): (12611, 13084),
        (200, "MID", "NEXUS_2"): (13052, 12612),
    }

    def _build_tower_states(self):
        """Build tower state tracking with known positions + BUILDING_KILL events."""
        for key, (x, y) in self._TOWER_POSITIONS.items():
            team, lane, ttype = key
            self._tower_states[key] = {
                "alive": True,
                "destroyed_ms": None,
                "x": x,
                "y": y,
                "team": team,
                "lane": lane,
                "type": ttype,
            }

        # Match BUILDING_KILL events to closest known tower
        matched = set()
        for b in sorted(self._buildings, key=lambda e: e["timestamp_ms"]):
            if b["building_type"] != "TOWER_BUILDING":
                continue
            bx, by = b["x"], b["y"]
            owner_team = b["killer_team"]  # teamId = team that owns the tower

            best_key = None
            best_dist = float("inf")
            for key, (tx, ty) in self._TOWER_POSITIONS.items():
                if key in matched or key[0] != owner_team:
                    continue
                dist = math.sqrt((bx - tx) ** 2 + (by - ty) ** 2)
                if dist < best_dist:
                    best_dist = dist
                    best_key = key

            if best_key and best_dist < 2000:
                self._tower_states[best_key]["alive"] = False
                self._tower_states[best_key]["destroyed_ms"] = b["timestamp_ms"]
                self._tower_states[best_key]["x"] = bx
                self._tower_states[best_key]["y"] = by
                matched.add(best_key)

    def _detect_recalls(self):
        """Detect recalls by position jumps to base between frames."""
        BASE_RADIUS = 2500
        MIN_DISTANCE = 3500
        RECALL_DURATION_MS = 8000

        for pid in self.pid_map:
            team_id = self.pid_map[pid]["team_id"]
            base_x, base_y = self._base_positions.get(team_id, (0, 0))

            for i in range(1, len(self._frames)):
                prev_pos = self._frames[i - 1]["positions"].get(pid, (0, 0))
                curr_pos = self._frames[i]["positions"].get(pid, (0, 0))

                if prev_pos == (0, 0) or curr_pos == (0, 0):
                    continue

                prev_dist = math.sqrt(
                    (prev_pos[0] - base_x) ** 2 + (prev_pos[1] - base_y) ** 2
                )
                curr_dist = math.sqrt(
                    (curr_pos[0] - base_x) ** 2 + (curr_pos[1] - base_y) ** 2
                )

                # Was far from base, now at base → likely recalled
                if prev_dist > MIN_DISTANCE and curr_dist < BASE_RADIUS:
                    frame_ts = self._frames[i]["timestamp_ms"]
                    recall_start = max(0, frame_ts - RECALL_DURATION_MS)

                    # Check for item purchase near arrival (confirms recall)
                    has_purchase = any(
                        ip["pid"] == pid and abs(ip["timestamp_ms"] - frame_ts) < 30000
                        for ip in self._item_purchases
                    )

                    self._recalls.append({
                        "timestamp_ms": recall_start,
                        "pid": pid,
                        "end_ms": frame_ts,
                        "has_purchase": has_purchase,
                    })

        self._recalls.sort(key=lambda r: r["timestamp_ms"])

    def _build_death_timers(self):
        """Build death timer data from CHAMPION_KILL events."""
        for pid in self.pid_map:
            self._death_timers[pid] = []

        for kill in self._kills:
            victim = kill["victim_pid"]
            ts = kill["timestamp_ms"]

            # Get victim level at time of death
            frame_idx = max(0, min(ts // 60000, len(self._frames) - 1))
            level = self._frames[frame_idx]["stats"].get(victim, {}).get("level", 1)

            respawn_ms = self._calc_respawn_time(level, ts)
            if victim in self._death_timers:
                self._death_timers[victim].append((ts, ts + respawn_ms))

    @staticmethod
    def _calc_respawn_time(level, game_time_ms):
        """Calculate respawn time in ms (approximate League formula)."""
        BRW = [0, 6, 6, 8, 8, 10, 12, 16, 21, 26, 30, 32.5, 35, 37.5, 40, 42.5, 45, 47.5, 52.5]
        base = BRW[min(level, 18)] if 1 <= level <= 18 else 52.5

        # Time increase after 15 minutes
        game_min = game_time_ms / 60000
        if game_min > 15:
            base += min((game_min - 15) * 0.6, 15)

        return int(base * 1000)

    # ===================================================================
    #  QUERIES (chamadas a cada frame de animacao)
    # ===================================================================

    def get_opponent_pid(self):
        """Identifica oponente direto (mesmo role, time oposto)."""
        if not self.target_pid:
            return None
        target_info = self.pid_map.get(self.target_pid, {})
        target_role = target_info.get("position", "")
        enemy_team = 200 if self.target_team == 100 else 100

        for pid, info in self.pid_map.items():
            if info["team_id"] == enemy_team and info["position"] == target_role:
                return pid
        return None

    def get_positions_at(self, game_time_ms):
        """Retorna posicoes interpoladas de todos os jogadores."""
        if not self._frames:
            return {}

        game_time_ms = max(0, min(game_time_ms, self.game_duration_ms))

        # Indice do frame
        frame_interval = 60000  # 1 minuto
        idx = game_time_ms / frame_interval
        idx_before = int(idx)
        idx_after = idx_before + 1

        idx_before = max(0, min(idx_before, len(self._frames) - 1))
        idx_after = max(0, min(idx_after, len(self._frames) - 1))

        t = idx - int(idx) if idx_before != idx_after else 0

        positions = {}
        pos_before = self._frames[idx_before]["positions"]
        pos_after = self._frames[idx_after]["positions"]

        for pid in self.pid_map:
            x1, y1 = pos_before.get(pid, (0, 0))
            x2, y2 = pos_after.get(pid, (0, 0))

            # Se uma posicao e invalida, usa a outra
            if x1 == 0 and y1 == 0:
                positions[pid] = (x2, y2)
            elif x2 == 0 and y2 == 0:
                positions[pid] = (x1, y1)
            else:
                positions[pid] = (
                    int(x1 + (x2 - x1) * t),
                    int(y1 + (y2 - y1) * t),
                )

        return positions

    def get_stats_at(self, game_time_ms):
        """Retorna level/gold/cs/kda de cada jogador no frame mais proximo."""
        if not self._frames:
            return {}

        frame_idx = min(game_time_ms // 60000, len(self._frames) - 1)
        frame_idx = max(0, frame_idx)

        result = {}
        frame_stats = self._frames[frame_idx]["stats"]
        kda = self._kda_by_frame.get(frame_idx, {})

        for pid in self.pid_map:
            s = frame_stats.get(pid, {})
            k = kda.get(pid, {"kills": 0, "deaths": 0, "assists": 0})
            result[pid] = {
                "level": s.get("level", 1),
                "gold": s.get("gold", 0),
                "cs": s.get("cs", 0),
                "kills": k["kills"],
                "deaths": k["deaths"],
                "assists": k["assists"],
            }

        return result

    def get_active_wards_at(self, game_time_ms):
        """Retorna wards visiveis no mapa no momento dado."""
        active = []
        for w in self._ward_lifetimes:
            if w["start_ms"] > game_time_ms:
                break  # Lista ordenada por start_ms
            if w["end_ms"] >= game_time_ms:
                active.append(w)
        return active

    def get_active_events_at(self, game_time_ms, window_ms=5000):
        """Retorna kills que devem estar visiveis (dentro da janela de tempo)."""
        start = game_time_ms - window_ms
        events = []

        # Binary search no array ordenado de kills
        timestamps = [k["timestamp_ms"] for k in self._kills]
        left = bisect.bisect_left(timestamps, start)
        right = bisect.bisect_right(timestamps, game_time_ms)

        for i in range(left, right):
            k = self._kills[i]
            age_ms = game_time_ms - k["timestamp_ms"]
            events.append({**k, "age_ms": age_ms, "event_type": "kill"})

        return events

    def get_active_objectives_at(self, game_time_ms, window_ms=8000):
        """Retorna objetivos que devem estar visiveis."""
        start = game_time_ms - window_ms
        events = []

        timestamps = [o["timestamp_ms"] for o in self._objectives]
        left = bisect.bisect_left(timestamps, start)
        right = bisect.bisect_right(timestamps, game_time_ms)

        for i in range(left, right):
            o = self._objectives[i]
            age_ms = game_time_ms - o["timestamp_ms"]
            events.append({**o, "age_ms": age_ms, "event_type": "objective"})

        # Buildings tambem
        timestamps_b = [b["timestamp_ms"] for b in self._buildings]
        left_b = bisect.bisect_left(timestamps_b, start)
        right_b = bisect.bisect_right(timestamps_b, game_time_ms)

        for i in range(left_b, right_b):
            b = self._buildings[i]
            age_ms = game_time_ms - b["timestamp_ms"]
            events.append({**b, "age_ms": age_ms, "event_type": "building"})

        return events

    def get_all_kills(self):
        return self._kills

    def get_all_objectives(self):
        return self._objectives

    def get_all_buildings(self):
        return self._buildings

    def get_teamfights(self):
        return self._teamfights

    def get_tower_states_at(self, game_time_ms):
        """Returns towers with alive/destroyed status at given time."""
        towers = []
        for key, state in self._tower_states.items():
            if state["destroyed_ms"] is None:
                alive = True
            else:
                alive = state["destroyed_ms"] > game_time_ms

            towers.append({
                "key": key,
                "x": state["x"],
                "y": state["y"],
                "team": state["team"],
                "lane": state["lane"],
                "type": state["type"],
                "alive": alive,
            })
        return towers

    def get_active_recalls_at(self, game_time_ms):
        """Returns recalls currently in progress."""
        active = []
        for r in self._recalls:
            if r["timestamp_ms"] <= game_time_ms <= r["end_ms"]:
                duration = max(1, r["end_ms"] - r["timestamp_ms"])
                progress = min(1.0, (game_time_ms - r["timestamp_ms"]) / duration)
                active.append({**r, "progress": progress})
        return active

    def is_dead_at(self, pid, game_time_ms):
        """Check if player is dead. Returns (is_dead, respawn_ms)."""
        timers = self._death_timers.get(pid, [])
        for death_ms, respawn_ms in timers:
            if death_ms <= game_time_ms < respawn_ms:
                return True, respawn_ms
        return False, 0

    def get_active_level_ups_at(self, game_time_ms, window_ms=3000):
        """Returns level-ups within time window for flash effect."""
        start = game_time_ms - window_ms
        active = []
        timestamps = [lu["timestamp_ms"] for lu in self._level_ups]
        left = bisect.bisect_left(timestamps, start)
        right = bisect.bisect_right(timestamps, game_time_ms)
        for i in range(left, right):
            lu = self._level_ups[i]
            active.append({**lu, "age_ms": game_time_ms - lu["timestamp_ms"]})
        return active

    def get_active_special_kills_at(self, game_time_ms, window_ms=5000):
        """Returns special kills (multi-kill, first blood) within window."""
        start = game_time_ms - window_ms
        active = []
        timestamps = [sk["timestamp_ms"] for sk in self._special_kills]
        left = bisect.bisect_left(timestamps, start)
        right = bisect.bisect_right(timestamps, game_time_ms)
        for i in range(left, right):
            sk = self._special_kills[i]
            active.append({**sk, "age_ms": game_time_ms - sk["timestamp_ms"]})
        return active

    def get_all_recalls(self):
        return self._recalls

    def get_all_level_ups(self):
        return self._level_ups

    def get_all_special_kills(self):
        return self._special_kills

    @staticmethod
    def game_to_canvas(game_x, game_y, canvas_size):
        """Converte coordenadas do jogo para coordenadas do Canvas."""
        cx = int(game_x / MAP_MAX_X * canvas_size)
        cy = int((1 - game_y / MAP_MAX_Y) * canvas_size)
        return max(0, min(canvas_size - 1, cx)), max(0, min(canvas_size - 1, cy))

    @staticmethod
    def format_time(ms):
        """Formata millisegundos como MM:SS."""
        total_sec = max(0, ms // 1000)
        return f"{total_sec // 60}:{total_sec % 60:02d}"
