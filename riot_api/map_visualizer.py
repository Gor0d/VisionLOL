# -*- coding: utf-8 -*-
"""
Visualizador de mapa do Summoner's Rift
- Baixa/cacheia minimap e icones de campeoes do Data Dragon
- Renderiza posicoes dos jogadores no mapa
- Gera imagem PIL pronta para exibir na GUI ou salvar
"""

import sys
import os
import io
import math
import requests
from PIL import Image, ImageDraw, ImageFont

# Logger com fallback
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from logger import get_logger
    logger = get_logger("MapVisualizer")
except Exception:
    class _DummyLogger:
        def debug(self, msg): pass
        def info(self, msg): print(f"[INFO] {msg}")
        def warning(self, msg): print(f"[WARNING] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
        def exception(self, msg): print(f"[EXCEPTION] {msg}")
    logger = _DummyLogger()

# Diretorio de cache para assets
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets_cache")

# Coordenadas do mapa do Summoner's Rift
# O mapa vai de aprox. (0, 0) a (14820, 14881)
# Mas as posicoes reais dos jogadores ficam entre ~400 e ~14400
MAP_MIN_X = 0
MAP_MIN_Y = 0
MAP_MAX_X = 14820
MAP_MAX_Y = 14881

# Tamanho do mapa renderizado
MAP_RENDER_SIZE = 800

# Tamanho dos icones no mapa
ICON_SIZE = 42

# Cores dos times
TEAM_COLORS = {
    100: (68, 114, 196),   # Azul (ORDER / Blue side)
    200: (196, 68, 68),    # Vermelho (CHAOS / Red side)
}

# Borda dos icones
BORDER_WIDTH = 3

# Cor do texto
TEXT_COLOR = (255, 255, 255)
TEXT_SHADOW = (0, 0, 0)


class MapVisualizer:
    """Renderiza posicoes de jogadores no mapa do Summoner's Rift"""

    _MAX_ICON_CACHE = 80  # ~80 campeões × ~40KB PIL = ~3MB máximo

    def __init__(self, match_api):
        self.match_api = match_api
        self._patch_version = None
        self._minimap = None
        self._champion_icons = {}   # insertion-order dict usado como LRU simples

        # Cria diretorio de cache
        os.makedirs(CACHE_DIR, exist_ok=True)
        os.makedirs(os.path.join(CACHE_DIR, "champions"), exist_ok=True)

    def _get_patch_version(self):
        """Obtem versao atual do patch do Data Dragon"""
        if self._patch_version:
            return self._patch_version

        try:
            resp = requests.get(
                "https://ddragon.leagueoflegends.com/api/versions.json", timeout=5
            )
            versions = resp.json()
            self._patch_version = versions[0]
            logger.info(f"Patch version: {self._patch_version}")
            return self._patch_version
        except Exception as e:
            logger.error(f"Erro ao obter versao do patch: {e}")
            return "16.4.1"  # fallback

    def _download_minimap(self):
        """Baixa e cacheia o minimap do Summoner's Rift"""
        cache_path = os.path.join(CACHE_DIR, "minimap.png")

        # Usa cache se existir
        if os.path.exists(cache_path):
            self._minimap = Image.open(cache_path).convert("RGBA")
            return self._minimap

        patch = self._get_patch_version()
        url = f"https://ddragon.leagueoflegends.com/cdn/{patch}/img/map/map11.png"

        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()

            img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
            img.save(cache_path)
            self._minimap = img
            logger.info("Minimap baixado e cacheado")
            return img
        except Exception as e:
            logger.error(f"Erro ao baixar minimap: {e}")
            return None

    def _download_champion_icon(self, champion_name):
        """Baixa e cacheia icone de um campeao"""
        # Normaliza nome (alguns tem espacos ou caracteres especiais)
        safe_name = champion_name.replace(" ", "").replace("'", "")

        # Nomes especiais que o Data Dragon usa diferente
        name_fixes = {
            "FiddleSticks": "Fiddlesticks",
            "Wukong": "MonkeyKing",
            "LeBlanc": "Leblanc",
            "Kai'Sa": "Kaisa",
            "Kha'Zix": "Khazix",
            "Bel'Veth": "Belveth",
            "Cho'Gath": "Chogath",
            "Vel'Koz": "Velkoz",
            "Rek'Sai": "RekSai",
            "Kog'Maw": "KogMaw",
            "K'Sante": "KSante",
        }
        api_name = name_fixes.get(champion_name, safe_name)

        cache_path = os.path.join(CACHE_DIR, "champions", f"{api_name}.png")

        if os.path.exists(cache_path):
            if champion_name in self._champion_icons:
                return self._champion_icons[champion_name]
            img = Image.open(cache_path).convert("RGBA")
            self._evict_icon_cache()
            self._champion_icons[champion_name] = img
            return img

        patch = self._get_patch_version()
        url = f"https://ddragon.leagueoflegends.com/cdn/{patch}/img/champion/{api_name}.png"

        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()

            img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
            img.save(cache_path)
            self._evict_icon_cache()
            self._champion_icons[champion_name] = img
            return img
        except Exception as e:
            logger.warning(f"Erro ao baixar icone de {champion_name} ({api_name}): {e}")
            # Tenta sem fix
            if api_name != safe_name:
                try:
                    url2 = f"https://ddragon.leagueoflegends.com/cdn/{patch}/img/champion/{safe_name}.png"
                    resp2 = requests.get(url2, timeout=10)
                    resp2.raise_for_status()
                    img = Image.open(io.BytesIO(resp2.content)).convert("RGBA")
                    img.save(cache_path)
                    self._evict_icon_cache()
                    self._champion_icons[champion_name] = img
                    return img
                except Exception:
                    pass
            return None

    def _evict_icon_cache(self):
        """Remove as entradas mais antigas se o cache ultrapassar o limite."""
        if len(self._champion_icons) >= self._MAX_ICON_CACHE:
            to_remove = list(self._champion_icons.keys())[:10]
            for k in to_remove:
                del self._champion_icons[k]

    def _download_item_icon(self, item_id: int):
        """Baixa e cacheia ícone de item pelo ID. Retorna PIL Image ou None."""
        if not item_id:
            return None
        cache_path = os.path.join(CACHE_DIR, "items", f"{item_id}.png")
        os.makedirs(os.path.join(CACHE_DIR, "items"), exist_ok=True)

        if os.path.exists(cache_path):
            try:
                return Image.open(cache_path).convert("RGBA")
            except Exception:
                pass

        patch = self._get_patch_version()
        url   = f"https://ddragon.leagueoflegends.com/cdn/{patch}/img/item/{item_id}.png"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
            img.save(cache_path)
            return img
        except Exception as e:
            logger.debug(f"Ícone do item {item_id} não encontrado: {e}")
            return None

    def _game_to_map_coords(self, game_x, game_y, map_size):
        """Converte coordenadas do jogo para coordenadas na imagem do mapa"""
        # X do jogo -> X da imagem (proporcional)
        img_x = int((game_x - MAP_MIN_X) / (MAP_MAX_X - MAP_MIN_X) * map_size)

        # Y do jogo -> Y da imagem (INVERTIDO: y=0 no jogo é embaixo, y=0 na imagem é em cima)
        img_y = int((1 - (game_y - MAP_MIN_Y) / (MAP_MAX_Y - MAP_MIN_Y)) * map_size)

        # Clamp para ficar dentro dos limites
        img_x = max(0, min(map_size - 1, img_x))
        img_y = max(0, min(map_size - 1, img_y))

        return img_x, img_y

    def _create_bordered_icon(self, icon, team_id, size=ICON_SIZE):
        """Cria icone com borda colorida do time"""
        border = BORDER_WIDTH
        total = size + border * 2

        # Fundo com cor do time
        color = TEAM_COLORS.get(team_id, (128, 128, 128))
        bordered = Image.new("RGBA", (total, total), color + (255,))

        # Redimensiona icone
        icon_resized = icon.resize((size, size), Image.Resampling.LANCZOS)

        # Cola icone no centro
        bordered.paste(icon_resized, (border, border))

        # Mascara circular
        mask = Image.new("L", (total, total), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse([0, 0, total - 1, total - 1], fill=255)

        # Aplica mascara
        result = Image.new("RGBA", (total, total), (0, 0, 0, 0))
        result.paste(bordered, mask=mask)

        return result

    def render_match_positions(self, match_id, target_puuid, frame_index=1, title=None):
        """
        Renderiza posicoes dos jogadores no mapa para um frame especifico.

        Args:
            match_id: ID da partida
            target_puuid: PUUID do jogador alvo (destacado)
            frame_index: Indice do frame na timeline (0=inicio, 1=minuto 1, etc.)
            title: Titulo opcional para o mapa

        Returns:
            PIL.Image com o mapa renderizado, ou None em caso de erro
        """
        # 1. Busca dados
        match_data = self.match_api.get_match_data(match_id)
        timeline = self.match_api.get_match_timeline(match_id)

        if not match_data or not timeline:
            logger.error("Nao foi possivel obter dados da partida")
            return None

        # 2. Mapeia participantes
        participants = match_data.get("info", {}).get("participants", [])
        pid_map = {}
        target_pid = None
        for p in participants:
            pid = p.get("participantId")
            pid_map[pid] = {
                "champion": p.get("championName", "?"),
                "position": p.get("teamPosition", "?"),
                "team_id": p.get("teamId", 100),
                "summoner": p.get("riotIdGameName", p.get("summonerName", "?")),
            }
            if p.get("puuid") == target_puuid:
                target_pid = pid

        # 3. Obtem posicoes do frame
        frames = timeline.get("info", {}).get("frames", [])
        if frame_index >= len(frames):
            frame_index = min(frame_index, len(frames) - 1)

        frame = frames[frame_index]
        participant_frames = frame.get("participantFrames", {})
        timestamp_ms = frame.get("timestamp", 0)
        minute = timestamp_ms // 60000

        # 4. Baixa assets
        minimap = self._download_minimap()
        if minimap is None:
            logger.error("Nao foi possivel obter o minimap")
            return None

        # 5. Cria imagem base (mapa redimensionado)
        map_img = minimap.resize((MAP_RENDER_SIZE, MAP_RENDER_SIZE), Image.Resampling.LANCZOS)

        # Adiciona overlay escuro para melhor contraste
        overlay = Image.new("RGBA", map_img.size, (0, 0, 0, 60))
        map_img = Image.alpha_composite(map_img, overlay)

        draw = ImageDraw.Draw(map_img)

        # 6. Tenta carregar fonte
        try:
            font_title = ImageFont.truetype("arial.ttf", 20)
            font_label = ImageFont.truetype("arial.ttf", 12)
            font_small = ImageFont.truetype("arial.ttf", 10)
        except Exception:
            font_title = ImageFont.load_default()
            font_label = font_title
            font_small = font_title

        # 7. Desenha titulo
        if title is None:
            title = f"Posicionamento - Minuto {minute}"

        # Fundo do titulo
        draw.rectangle([0, 0, MAP_RENDER_SIZE, 35], fill=(0, 0, 0, 180))
        draw.text((MAP_RENDER_SIZE // 2, 8), title, fill=TEXT_COLOR,
                  font=font_title, anchor="mt")

        # 8. Desenha cada jogador
        icon_total_size = ICON_SIZE + BORDER_WIDTH * 2

        for pid_str, pf in participant_frames.items():
            pid = int(pid_str)
            pos = pf.get("position", {})
            game_x = pos.get("x", 0)
            game_y = pos.get("y", 0)

            if game_x == 0 and game_y == 0:
                continue

            info = pid_map.get(pid, {})
            champion = info.get("champion", "?")
            team_id = info.get("team_id", 100)
            position = info.get("position", "?")

            # Converte coordenadas
            img_x, img_y = self._game_to_map_coords(game_x, game_y, MAP_RENDER_SIZE)

            # Baixa e renderiza icone
            icon = self._download_champion_icon(champion)
            if icon:
                bordered_icon = self._create_bordered_icon(icon, team_id)

                # Posiciona icone centralizado no ponto
                paste_x = img_x - icon_total_size // 2
                paste_y = img_y - icon_total_size // 2

                # Clamp para nao sair da imagem
                paste_x = max(0, min(MAP_RENDER_SIZE - icon_total_size, paste_x))
                paste_y = max(0, min(MAP_RENDER_SIZE - icon_total_size, paste_y))

                map_img.paste(bordered_icon, (paste_x, paste_y), bordered_icon)

                # Destaque para o jogador alvo
                if pid == target_pid:
                    cx = paste_x + icon_total_size // 2
                    cy = paste_y + icon_total_size // 2
                    r = icon_total_size // 2 + 4
                    draw.ellipse(
                        [cx - r, cy - r, cx + r, cy + r],
                        outline=(255, 215, 0), width=3
                    )

                # Label do campeao
                label = f"{champion}"
                label_y = paste_y + icon_total_size + 2

                # Sombra do texto
                draw.text((paste_x + icon_total_size // 2 + 1, label_y + 1),
                          label, fill=TEXT_SHADOW, font=font_small, anchor="mt")
                # Texto
                draw.text((paste_x + icon_total_size // 2, label_y),
                          label, fill=TEXT_COLOR, font=font_small, anchor="mt")

            else:
                # Fallback: circulo colorido
                color = TEAM_COLORS.get(team_id, (128, 128, 128))
                r = 15
                draw.ellipse([img_x - r, img_y - r, img_x + r, img_y + r],
                             fill=color, outline=TEXT_COLOR, width=2)
                draw.text((img_x, img_y + r + 5), champion,
                          fill=TEXT_COLOR, font=font_small, anchor="mt")

        # 9. Legenda
        legend_y = MAP_RENDER_SIZE - 50
        draw.rectangle([0, legend_y, MAP_RENDER_SIZE, MAP_RENDER_SIZE], fill=(0, 0, 0, 180))

        # Time azul
        draw.ellipse([15, legend_y + 10, 30, legend_y + 25],
                     fill=TEAM_COLORS[100])
        draw.text((35, legend_y + 11), "Blue Side (ORDER)",
                  fill=TEXT_COLOR, font=font_small)

        # Time vermelho
        draw.ellipse([220, legend_y + 10, 235, legend_y + 25],
                     fill=TEAM_COLORS[200])
        draw.text((240, legend_y + 11), "Red Side (CHAOS)",
                  fill=TEXT_COLOR, font=font_small)

        # Destaque do jogador
        draw.ellipse([430, legend_y + 8, 448, legend_y + 26],
                     outline=(255, 215, 0), width=2)
        draw.text((453, legend_y + 11), "Voce",
                  fill=(255, 215, 0), font=font_small)

        # Minuto
        draw.text((MAP_RENDER_SIZE - 15, legend_y + 11),
                  f"Min {minute}", fill=self._minute_color(minute),
                  font=font_label, anchor="rt")

        # 10. Borda do destaque (borda dourada no jogador alvo)
        draw.rectangle([0, 0, MAP_RENDER_SIZE - 1, MAP_RENDER_SIZE - 1],
                        outline=(60, 60, 60), width=2)

        return map_img.convert("RGB")

    def render_early_game(self, match_id, target_puuid):
        """
        Renderiza o posicionamento do nivel 1 (primeiro minuto).
        Usa frame_index=1 (minuto 1) pois frame 0 geralmente tem todos na base.
        """
        return self.render_match_positions(
            match_id, target_puuid,
            frame_index=1,
            title="Posicionamento Level 1"
        )

    def render_multi_frame(self, match_id, target_puuid, frame_indices=None):
        """
        Renderiza multiplos frames lado a lado.

        Args:
            frame_indices: Lista de indices de frame (ex: [1, 5, 10, 15])

        Returns:
            PIL.Image com os mapas lado a lado
        """
        if frame_indices is None:
            frame_indices = [1, 5, 10, 15]

        images = []
        for fi in frame_indices:
            img = self.render_match_positions(
                match_id, target_puuid,
                frame_index=fi,
                title=f"Minuto {fi}"
            )
            if img:
                images.append(img)

        if not images:
            return None

        # Calcula layout em grid
        n = len(images)
        cols = min(n, 2)
        rows = math.ceil(n / cols)

        single_w = images[0].width // 2  # Metade do tamanho para caber
        single_h = images[0].height // 2

        total_w = cols * single_w + (cols - 1) * 4
        total_h = rows * single_h + (rows - 1) * 4

        grid = Image.new("RGB", (total_w, total_h), (30, 30, 30))

        for i, img in enumerate(images):
            r = i // cols
            c = i % cols
            resized = img.resize((single_w, single_h), Image.Resampling.LANCZOS)
            x = c * (single_w + 4)
            y = r * (single_h + 4)
            grid.paste(resized, (x, y))

        return grid

    def _minute_color(self, minute):
        """Retorna cor baseada no minuto (early/mid/late game)"""
        if minute <= 5:
            return (100, 200, 255)   # Azul claro - early
        elif minute <= 15:
            return (255, 255, 100)   # Amarelo - mid
        else:
            return (255, 100, 100)   # Vermelho - late
