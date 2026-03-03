# -*- coding: utf-8 -*-
"""
Visualizador de Pathing - Timeline de movimentacao no mapa
Renderiza pathing de junglers, wards, kills, objetivos com filtros
"""

import sys
import os
import math
from PIL import Image, ImageDraw, ImageFont

# Logger com fallback
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from logger import get_logger
    logger = get_logger("PathingViz")
except Exception:
    class _DummyLogger:
        def debug(self, msg): pass
        def info(self, msg): print(f"[INFO] {msg}")
        def warning(self, msg): print(f"[WARNING] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
        def exception(self, msg): print(f"[EXCEPTION] {msg}")
    logger = _DummyLogger()

# Constantes de renderizacao
MAP_SIZE = 800
MAP_MIN_X, MAP_MIN_Y = 0, 0
MAP_MAX_X, MAP_MAX_Y = 14820, 14881

# Cores
COLOR_MY_PATH = (0, 180, 216)       # Ciano
COLOR_ENEMY_PATH = (239, 71, 111)   # Vermelho
COLOR_MY_WARD = (255, 214, 10)      # Amarelo
COLOR_ENEMY_WARD = (180, 50, 50)    # Vermelho escuro
COLOR_MY_KILL = (6, 214, 160)       # Verde
COLOR_MY_DEATH = (239, 71, 111)     # Vermelho
COLOR_OBJECTIVE = (160, 80, 220)    # Roxo
COLOR_BUILDING = (230, 150, 50)     # Laranja
COLOR_TEXT = (255, 255, 255)
COLOR_TEXT_SHADOW = (0, 0, 0)
COLOR_DIM = (120, 120, 120)


class PathingData:
    """Dados pre-processados para renderizacao de pathing"""

    def __init__(self):
        self.paths = {}          # {pid: [(minute, x, y), ...]}
        self.wards_placed = []   # [{minute, x, y, ward_type, team_id, creator_pid}]
        self.wards_killed = []   # [{minute, x, y, ward_type, killer_pid}]
        self.kills = []          # [{minute, x, y, killer_pid, victim_pid, assisters}]
        self.objectives = []     # [{minute, x, y, monster_type, sub_type, killer_team}]
        self.buildings = []      # [{minute, x, y, killer_team}]
        self.target_pid = None
        self.target_team = None
        self.enemy_jungler_pid = None
        self.pid_map = {}        # {pid: {champion, position, team_id}}
        self.game_duration_min = 0


class PathingVisualizer:
    """Renderiza pathing de jogadores no mapa com camadas filtraveis"""

    def __init__(self, map_visualizer):
        """
        Args:
            map_visualizer: MapVisualizer existente (para reusar minimap/icones)
        """
        self.map_viz = map_visualizer

    def extract_pathing_data(self, timeline, match_data, target_puuid):
        """Extrai todos os dados de pathing da timeline"""
        data = PathingData()

        participants = match_data.get("info", {}).get("participants", [])
        frames = timeline.get("info", {}).get("frames", [])
        data.game_duration_min = len(frames) - 1

        # Mapeia participantes
        for p in participants:
            pid = p.get("participantId")
            data.pid_map[pid] = {
                "champion": p.get("championName", "?"),
                "position": p.get("teamPosition", "?"),
                "team_id": p.get("teamId", 100),
            }
            if p.get("puuid") == target_puuid:
                data.target_pid = pid
                data.target_team = p.get("teamId", 100)

        # Identifica jungler inimigo
        enemy_team = 200 if data.target_team == 100 else 100
        for pid, info in data.pid_map.items():
            if info["team_id"] == enemy_team and info["position"] == "JUNGLE":
                data.enemy_jungler_pid = pid
                break

        # Extrai posicoes por frame (pathing)
        for frame in frames:
            timestamp_ms = frame.get("timestamp", 0)
            minute = timestamp_ms // 60000
            pframes = frame.get("participantFrames", {})

            for pid_str, pf in pframes.items():
                pid = int(pid_str)
                pos = pf.get("position", {})
                x, y = pos.get("x", 0), pos.get("y", 0)
                if x == 0 and y == 0:
                    continue

                if pid not in data.paths:
                    data.paths[pid] = []
                data.paths[pid].append((minute, x, y))

        # Extrai eventos
        for frame in frames:
            for event in frame.get("events", []):
                etype = event.get("type")
                ts = event.get("timestamp", 0)
                minute = ts // 60000

                if etype == "CHAMPION_KILL":
                    pos = event.get("position", {})
                    data.kills.append({
                        "minute": minute,
                        "timestamp_ms": ts,
                        "x": pos.get("x", 0),
                        "y": pos.get("y", 0),
                        "killer_pid": event.get("killerId", 0),
                        "victim_pid": event.get("victimId", 0),
                        "assisters": event.get("assistingParticipantIds", []),
                    })

                elif etype == "WARD_PLACED":
                    creator = event.get("creatorId", 0)
                    ward_type = event.get("wardType", "UNDEFINED")
                    # Estima posicao por interpolacao
                    ix, iy = self._interpolate_position(creator, ts, frames)
                    if ix and iy:
                        team_id = data.pid_map.get(creator, {}).get("team_id", 0)
                        data.wards_placed.append({
                            "minute": minute,
                            "timestamp_ms": ts,
                            "x": ix, "y": iy,
                            "ward_type": ward_type,
                            "team_id": team_id,
                            "creator_pid": creator,
                        })

                elif etype == "WARD_KILL":
                    killer = event.get("killerId", 0)
                    ward_type = event.get("wardType", "UNDEFINED")
                    ix, iy = self._interpolate_position(killer, ts, frames)
                    if ix and iy:
                        data.wards_killed.append({
                            "minute": minute,
                            "timestamp_ms": ts,
                            "x": ix, "y": iy,
                            "ward_type": ward_type,
                            "killer_pid": killer,
                        })

                elif etype == "ELITE_MONSTER_KILL":
                    pos = event.get("position", {})
                    data.objectives.append({
                        "minute": minute,
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
                    data.buildings.append({
                        "minute": minute,
                        "timestamp_ms": ts,
                        "x": pos.get("x", 0),
                        "y": pos.get("y", 0),
                        "building_type": event.get("buildingType", ""),
                        "killer_team": event.get("teamId", 0),
                    })

        logger.info(
            f"PathingData extraido: {len(data.paths.get(data.target_pid, []))} pontos target, "
            f"{len(data.kills)} kills, {len(data.wards_placed)} wards, "
            f"{len(data.objectives)} objetivos"
        )
        return data

    def _interpolate_position(self, pid, timestamp_ms, frames):
        """Estima posicao de um jogador em um timestamp entre frames"""
        minute_float = timestamp_ms / 60000.0
        frame_before = int(minute_float)
        frame_after = frame_before + 1

        if frame_before < 0:
            frame_before = 0
        if frame_after >= len(frames):
            frame_after = len(frames) - 1
        if frame_before >= len(frames):
            return None, None

        # Posicao no frame anterior
        pf_before = frames[frame_before].get("participantFrames", {}).get(str(pid), {})
        pos_before = pf_before.get("position", {})
        x1, y1 = pos_before.get("x", 0), pos_before.get("y", 0)

        if x1 == 0 and y1 == 0:
            return None, None

        if frame_before == frame_after:
            return x1, y1

        # Posicao no frame posterior
        pf_after = frames[frame_after].get("participantFrames", {}).get(str(pid), {})
        pos_after = pf_after.get("position", {})
        x2, y2 = pos_after.get("x", 0), pos_after.get("y", 0)

        if x2 == 0 and y2 == 0:
            return x1, y1

        # Interpolacao linear
        t = minute_float - frame_before
        ix = int(x1 + (x2 - x1) * t)
        iy = int(y1 + (y2 - y1) * t)
        return ix, iy

    def render(self, pathing_data, filters, max_minute=None):
        """
        Renderiza o mapa com camadas baseado nos filtros.

        Args:
            pathing_data: PathingData pre-processado
            filters: dict com chaves booleanas:
                my_path, enemy_path, my_wards, enemy_wards,
                my_kills, my_deaths, objectives, buildings
            max_minute: Se definido, so mostra dados ate este minuto

        Returns:
            PIL.Image (800x800 RGB)
        """
        d = pathing_data
        if max_minute is None:
            max_minute = d.game_duration_min

        # Mapa base
        minimap = self.map_viz._download_minimap()
        if minimap is None:
            return None

        map_img = minimap.resize((MAP_SIZE, MAP_SIZE), Image.Resampling.LANCZOS)
        overlay = Image.new("RGBA", map_img.size, (0, 0, 0, 80))
        map_img = Image.alpha_composite(map_img, overlay)

        draw = ImageDraw.Draw(map_img)

        try:
            font_title = ImageFont.truetype("arial.ttf", 18)
            font_label = ImageFont.truetype("arial.ttf", 11)
            font_small = ImageFont.truetype("arial.ttf", 9)
            font_minute = ImageFont.truetype("arial.ttf", 8)
        except Exception:
            font_title = ImageFont.load_default()
            font_label = font_title
            font_small = font_title
            font_minute = font_title

        # === CAMADA: Pathing ===
        if filters.get("enemy_path") and d.enemy_jungler_pid:
            path = d.paths.get(d.enemy_jungler_pid, [])
            self._draw_path(draw, path, COLOR_ENEMY_PATH, max_minute, dashed=True, font=font_minute)

        if filters.get("my_path") and d.target_pid:
            path = d.paths.get(d.target_pid, [])
            self._draw_path(draw, path, COLOR_MY_PATH, max_minute, dashed=False, font=font_minute)

        # === CAMADA: Wards ===
        if filters.get("my_wards"):
            for w in d.wards_placed:
                if w["minute"] > max_minute:
                    continue
                if w["team_id"] == d.target_team:
                    self._draw_ward_marker(draw, w["x"], w["y"], w["ward_type"], False, font_small)

        if filters.get("enemy_wards"):
            for w in d.wards_placed:
                if w["minute"] > max_minute:
                    continue
                if w["team_id"] != d.target_team:
                    self._draw_ward_marker(draw, w["x"], w["y"], w["ward_type"], True, font_small)

        # === CAMADA: Kills/Deaths ===
        if filters.get("my_kills"):
            for k in d.kills:
                if k["minute"] > max_minute:
                    continue
                if k["killer_pid"] == d.target_pid or d.target_pid in k.get("assisters", []):
                    self._draw_kill_marker(draw, k["x"], k["y"], True,
                                           k["minute"], d.pid_map.get(k["victim_pid"], {}), font_small)

        if filters.get("my_deaths"):
            for k in d.kills:
                if k["minute"] > max_minute:
                    continue
                if k["victim_pid"] == d.target_pid:
                    self._draw_kill_marker(draw, k["x"], k["y"], False,
                                           k["minute"], d.pid_map.get(k["killer_pid"], {}), font_small)

        # === CAMADA: Objetivos ===
        if filters.get("objectives"):
            for obj in d.objectives:
                if obj["minute"] > max_minute:
                    continue
                self._draw_objective_marker(draw, obj["x"], obj["y"],
                                             obj["monster_type"], obj["sub_type"],
                                             obj["killer_team"], d.target_team, font_small)

        # === CAMADA: Torres ===
        if filters.get("buildings"):
            for b in d.buildings:
                if b["minute"] > max_minute:
                    continue
                self._draw_building_marker(draw, b["x"], b["y"],
                                            b["killer_team"], d.target_team, font_small)

        # === HEADER ===
        draw.rectangle([0, 0, MAP_SIZE, 32], fill=(0, 0, 0, 200))
        target_champ = d.pid_map.get(d.target_pid, {}).get("champion", "?")
        enemy_champ = d.pid_map.get(d.enemy_jungler_pid, {}).get("champion", "?") if d.enemy_jungler_pid else "?"
        title = f"Pathing: {target_champ} vs {enemy_champ} (Min 0-{max_minute})"
        draw.text((MAP_SIZE // 2, 6), title, fill=COLOR_TEXT, font=font_title, anchor="mt")

        # === LEGENDA ===
        self._draw_legend(draw, d, filters, font_small)

        # Borda
        draw.rectangle([0, 0, MAP_SIZE - 1, MAP_SIZE - 1], outline=(60, 60, 60), width=2)

        return map_img.convert("RGB")

    def _game_to_img(self, gx, gy):
        """Converte coordenadas do jogo para coordenadas da imagem"""
        ix = int((gx - MAP_MIN_X) / (MAP_MAX_X - MAP_MIN_X) * MAP_SIZE)
        iy = int((1 - (gy - MAP_MIN_Y) / (MAP_MAX_Y - MAP_MIN_Y)) * MAP_SIZE)
        return max(0, min(MAP_SIZE - 1, ix)), max(0, min(MAP_SIZE - 1, iy))

    def _draw_path(self, draw, path_points, base_color, max_minute, dashed=False, font=None):
        """Desenha linha de pathing com gradiente temporal e pontos numerados"""
        filtered = [(m, x, y) for m, x, y in path_points if m <= max_minute]
        if len(filtered) < 2:
            return

        total = len(filtered)

        for i in range(1, total):
            m_prev, x_prev, y_prev = filtered[i - 1]
            m_curr, x_curr, y_curr = filtered[i]

            ix1, iy1 = self._game_to_img(x_prev, y_prev)
            ix2, iy2 = self._game_to_img(x_curr, y_curr)

            # Gradiente: mais claro no inicio, mais escuro no fim
            t = i / total
            r = int(base_color[0] * (0.4 + 0.6 * t))
            g = int(base_color[1] * (0.4 + 0.6 * t))
            b = int(base_color[2] * (0.4 + 0.6 * t))
            color = (r, g, b, 200)

            if dashed:
                self._draw_dashed_line(draw, ix1, iy1, ix2, iy2, color, width=2, dash_len=8)
            else:
                draw.line([(ix1, iy1), (ix2, iy2)], fill=color, width=3)

        # Pontos numerados nos nos
        for i, (minute, gx, gy) in enumerate(filtered):
            ix, iy = self._game_to_img(gx, gy)
            r = 6

            # Ponto
            t = i / max(total - 1, 1)
            pr = int(base_color[0] * (0.5 + 0.5 * t))
            pg = int(base_color[1] * (0.5 + 0.5 * t))
            pb = int(base_color[2] * (0.5 + 0.5 * t))

            draw.ellipse([ix - r, iy - r, ix + r, iy + r],
                         fill=(pr, pg, pb, 230), outline=COLOR_TEXT, width=1)

            # Numero do minuto
            if font:
                draw.text((ix, iy), str(minute), fill=COLOR_TEXT, font=font, anchor="mm")

    def _draw_dashed_line(self, draw, x1, y1, x2, y2, color, width=2, dash_len=8):
        """Desenha linha tracejada"""
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx * dx + dy * dy)
        if length == 0:
            return

        dx /= length
        dy /= length

        pos = 0
        drawing = True
        while pos < length:
            end = min(pos + dash_len, length)
            if drawing:
                sx = int(x1 + dx * pos)
                sy = int(y1 + dy * pos)
                ex = int(x1 + dx * end)
                ey = int(y1 + dy * end)
                draw.line([(sx, sy), (ex, ey)], fill=color, width=width)
            pos = end
            drawing = not drawing

    def _draw_ward_marker(self, draw, gx, gy, ward_type, is_enemy, font):
        """Desenha marcador de ward"""
        ix, iy = self._game_to_img(gx, gy)
        size = 5 if is_enemy else 7
        color = COLOR_ENEMY_WARD if is_enemy else COLOR_MY_WARD

        if ward_type == "CONTROL_WARD":
            # Quadrado
            draw.rectangle([ix - size, iy - size, ix + size, iy + size],
                           fill=color + (180,), outline=COLOR_TEXT, width=1)
        else:
            # Triangulo (trinket/sight ward)
            draw.polygon([(ix, iy - size - 2), (ix - size, iy + size), (ix + size, iy + size)],
                         fill=color + (180,), outline=COLOR_TEXT)

    def _draw_kill_marker(self, draw, gx, gy, is_kill, minute, other_info, font):
        """Desenha marcador de kill ou morte"""
        ix, iy = self._game_to_img(gx, gy)

        if is_kill:
            # Estrela verde (kill)
            color = COLOR_MY_KILL
            r = 10
            # Desenha estrela como dois triangulos
            draw.polygon([
                (ix, iy - r), (ix + 4, iy - 3), (ix + r, iy - 3),
                (ix + 5, iy + 2), (ix + 7, iy + r),
                (ix, iy + 5), (ix - 7, iy + r),
                (ix - 5, iy + 2), (ix - r, iy - 3), (ix - 4, iy - 3),
            ], fill=color + (220,), outline=COLOR_TEXT, width=1)
        else:
            # X vermelho (morte)
            color = COLOR_MY_DEATH
            r = 8
            w = 3
            draw.line([(ix - r, iy - r), (ix + r, iy + r)], fill=color, width=w)
            draw.line([(ix - r, iy + r), (ix + r, iy - r)], fill=color, width=w)
            # Circulo de fundo
            draw.ellipse([ix - r - 1, iy - r - 1, ix + r + 1, iy + r + 1],
                         outline=color, width=2)

        # Label com minuto e campeao
        champ = other_info.get("champion", "")
        label = f"{minute}' {champ}"
        draw.text((ix + 1, iy + 13), label, fill=COLOR_TEXT_SHADOW, font=font, anchor="mt")
        draw.text((ix, iy + 12), label, fill=COLOR_TEXT, font=font, anchor="mt")

    def _draw_objective_marker(self, draw, gx, gy, monster_type, sub_type,
                                killer_team, target_team, font):
        """Desenha marcador de objetivo (dragon, baron, herald)"""
        ix, iy = self._game_to_img(gx, gy)
        r = 12

        # Cor baseada em quem matou
        if killer_team == target_team:
            fill = COLOR_MY_KILL + (200,)
            outline = COLOR_MY_KILL
        else:
            fill = COLOR_ENEMY_PATH + (200,)
            outline = COLOR_ENEMY_PATH

        draw.ellipse([ix - r, iy - r, ix + r, iy + r],
                     fill=fill, outline=outline, width=2)

        # Letra no centro
        if monster_type == "DRAGON":
            letter = "D"
        elif monster_type == "BARON_NASHOR":
            letter = "B"
        elif monster_type == "RIFTHERALD":
            letter = "H"
        else:
            letter = "?"

        draw.text((ix, iy), letter, fill=COLOR_TEXT, font=font, anchor="mm")

        # Sub-tipo embaixo
        if sub_type:
            short = sub_type.replace("_DRAGON", "").replace("DRAGON", "")[:4]
            draw.text((ix, iy + r + 5), short, fill=COLOR_DIM, font=font, anchor="mt")

    def _draw_building_marker(self, draw, gx, gy, killer_team, target_team, font):
        """Desenha marcador de torre destruida"""
        ix, iy = self._game_to_img(gx, gy)
        size = 8

        if killer_team == target_team:
            color = COLOR_MY_KILL + (180,)
        else:
            color = COLOR_ENEMY_PATH + (180,)

        draw.rectangle([ix - size, iy - size, ix + size, iy + size],
                       fill=color, outline=COLOR_BUILDING, width=2)
        draw.text((ix, iy), "T", fill=COLOR_TEXT, font=font, anchor="mm")

    def _draw_legend(self, draw, data, filters, font):
        """Desenha legenda no rodape"""
        y = MAP_SIZE - 45
        draw.rectangle([0, y, MAP_SIZE, MAP_SIZE], fill=(0, 0, 0, 200))

        x = 15
        items = []

        if filters.get("my_path"):
            target_champ = data.pid_map.get(data.target_pid, {}).get("champion", "?")
            items.append((COLOR_MY_PATH, f"__ {target_champ}"))
        if filters.get("enemy_path") and data.enemy_jungler_pid:
            enemy_champ = data.pid_map.get(data.enemy_jungler_pid, {}).get("champion", "?")
            items.append((COLOR_ENEMY_PATH, f"-- {enemy_champ}"))
        if filters.get("my_wards"):
            items.append((COLOR_MY_WARD, "Ward"))
        if filters.get("enemy_wards"):
            items.append((COLOR_ENEMY_WARD, "Ward Ini"))
        if filters.get("my_kills"):
            items.append((COLOR_MY_KILL, "Kill"))
        if filters.get("my_deaths"):
            items.append((COLOR_MY_DEATH, "Morte"))
        if filters.get("objectives"):
            items.append((COLOR_OBJECTIVE, "Obj"))
        if filters.get("buildings"):
            items.append((COLOR_BUILDING, "Torre"))

        for color, label in items:
            draw.ellipse([x, y + 12, x + 10, y + 22], fill=color)
            draw.text((x + 14, y + 11), label, fill=COLOR_TEXT, font=font)
            x += len(label) * 7 + 25
            if x > MAP_SIZE - 50:
                break
