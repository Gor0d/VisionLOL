# -*- coding: utf-8 -*-
"""
DashboardViewer - Dashboard de perfil com histórico de partidas e mapa de calor.
Clique em qualquer partida na lista para filtrar o heatmap para aquela partida.
"""

import logging
import tkinter as tk
import threading
from PIL import Image, ImageTk, ImageFilter

logger = logging.getLogger(__name__)

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# ═══════════════════════════════════════════════════════════════════════
#  PALETA
# ═══════════════════════════════════════════════════════════════════════
BG_DARKEST  = "#0d1117"
BG_DARK     = "#161b22"
BG_MEDIUM   = "#1c2129"
BG_LIGHT    = "#21262d"
BORDER      = "#30363d"

ACCENT      = "#58a6ff"
SUCCESS     = "#3fb950"
DANGER      = "#f85149"
WARNING     = "#d29922"

TEXT_BRIGHT = "#ffffff"
TEXT_COLOR  = "#e6edf3"
TEXT_DIM    = "#7d8590"

ROW_WIN     = "#0f2a14"
ROW_LOSS    = "#2a0f0f"
ROW_SEL     = "#1a3a5f"   # fundo da linha selecionada

# Mapa do Summoner's Rift — mesmos valores de map_visualizer.py
MAP_MIN_X   = 0
MAP_MIN_Y   = 0
MAP_MAX_X   = 14820
MAP_MAX_Y   = 14881

HEATMAP_SIZE   = 340
MATCH_ICON_SZ  = 28


# ═══════════════════════════════════════════════════════════════════════
#  DASHBOARD VIEWER
# ═══════════════════════════════════════════════════════════════════════
class DashboardViewer:
    """Janela de dashboard com histórico de partidas e heatmap por partida."""

    def __init__(self, root, summaries, match_data_cache,
                 map_visualizer, match_api, puuid):
        self.root      = root
        self.summaries = summaries          # list[(match_id, summary_dict)]
        self.cache     = match_data_cache   # {match_id: match_data}
        self.map_viz   = map_visualizer
        self.match_api = match_api
        self.puuid     = puuid

        # Ícones de campeões {nome: PhotoImage}
        self._champ_icons: dict[str, ImageTk.PhotoImage] = {}

        # Estado do heatmap
        self._minimap: Image.Image | None = None
        self._match_densities: dict[str, "np.ndarray"] = {}   # por partida
        self._total_density:   "np.ndarray | None" = None     # soma de todas
        self._selected_id:     str | None = None              # None = todas

        # Linhas do histórico: {match_id: (container_frame, row_frame)}
        self._match_rows: dict[str, tuple[tk.Frame, tk.Frame]] = {}

        # Referência ao PhotoImage atual do heatmap (evita gc)
        self._heatmap_ph: ImageTk.PhotoImage | None = None
        self._closed = False

        self._build_window()
        self._load_champion_icons()
        self._render_match_history()
        self._render_champion_stats()
        self._start_heatmap_thread()

    # ─────────────────────────────────────────────────────────────────
    #  JANELA E LAYOUT
    # ─────────────────────────────────────────────────────────────────

    def _build_window(self):
        self.win = tk.Toplevel(self.root)
        self.win.title("VisionLOL — Dashboard")
        self.win.configure(bg=BG_DARKEST)
        self.win.geometry("960x660")
        self.win.resizable(True, True)
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_header()

        body = tk.Frame(self.win, bg=BG_DARKEST)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        left = tk.Frame(body, bg=BG_DARKEST)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        right = tk.Frame(body, bg=BG_DARKEST, width=380)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        right.pack_propagate(False)

        self._build_left_panel(left)
        self._build_right_panel(right)

    def _build_header(self):
        hdr = tk.Frame(self.win, bg=BG_DARK, height=52)
        hdr.pack(fill=tk.X, padx=10, pady=(10, 6))
        hdr.pack_propagate(False)

        tk.Label(hdr, text="📊  Dashboard do Jogador",
                 font=("Segoe UI", 13, "bold"),
                 bg=BG_DARK, fg=TEXT_BRIGHT).pack(side=tk.LEFT, padx=14, pady=12)

        total = len(self.summaries)
        wins  = sum(1 for _, s in self.summaries if s and s.get("win"))
        wr    = int(wins / total * 100) if total else 0

        stats = tk.Frame(hdr, bg=BG_DARK)
        stats.pack(side=tk.RIGHT, padx=14, pady=8)
        tk.Label(stats, text=f"{total} partidas", font=("Segoe UI", 10),
                 bg=BG_DARK, fg=TEXT_DIM).pack(side=tk.LEFT, padx=(0, 12))
        tk.Label(stats, text=f"{wins}V / {total - wins}D",
                 font=("Segoe UI", 10), bg=BG_DARK, fg=TEXT_COLOR
                 ).pack(side=tk.LEFT, padx=(0, 12))
        tk.Label(stats, text=f"WR  {wr}%",
                 font=("Segoe UI", 11, "bold"),
                 bg=BG_DARK, fg=SUCCESS if wr >= 50 else DANGER
                 ).pack(side=tk.LEFT)

    def _build_left_panel(self, parent):
        _section_label(parent, "HISTÓRICO DE PARTIDAS  —  clique para filtrar o mapa")
        self._hist_frame = tk.Frame(parent, bg=BG_DARKEST)
        self._hist_frame.pack(fill=tk.X)

        tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X, pady=(10, 4))

        _section_label(parent, "POOL DE CAMPEÕES")

        # Container scrollável para o pool de campeões
        champ_outer = tk.Frame(parent, bg=BG_DARKEST)
        champ_outer.pack(fill=tk.BOTH, expand=True)

        champ_scroll = tk.Scrollbar(champ_outer, orient="vertical")
        champ_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        champ_canvas = tk.Canvas(
            champ_outer, bg=BG_DARKEST,
            highlightthickness=0, yscrollcommand=champ_scroll.set
        )
        champ_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        champ_scroll.config(command=champ_canvas.yview)

        self._champ_frame = tk.Frame(champ_canvas, bg=BG_DARKEST)
        _win_id = champ_canvas.create_window((0, 0), window=self._champ_frame, anchor="nw")

        self._champ_frame.bind(
            "<Configure>",
            lambda e: champ_canvas.configure(scrollregion=champ_canvas.bbox("all"))
        )
        champ_canvas.bind(
            "<Configure>",
            lambda e: champ_canvas.itemconfig(_win_id, width=e.width)
        )
        champ_canvas.bind(
            "<MouseWheel>",
            lambda e: champ_canvas.yview_scroll(-1 * (e.delta // 120), "units")
        )

    def _build_right_panel(self, parent):
        _section_label(parent, "MAPA DE CALOR DE ATIVIDADE")

        # Subtítulo dinâmico (atualizado ao selecionar partida)
        self._heatmap_subtitle = tk.Label(
            parent,
            text="Todas as partidas",
            font=("Segoe UI", 8), bg=BG_DARKEST, fg=ACCENT
        )
        self._heatmap_subtitle.pack(anchor="w", padx=4, pady=(0, 4))

        self._heatmap_canvas = tk.Canvas(
            parent, width=HEATMAP_SIZE, height=HEATMAP_SIZE,
            bg=BG_MEDIUM, highlightthickness=1, highlightbackground=BORDER
        )
        self._heatmap_canvas.pack(padx=4)
        self._loading_id = self._heatmap_canvas.create_text(
            HEATMAP_SIZE // 2, HEATMAP_SIZE // 2,
            text="Baixando timelines…\n(pode levar alguns segundos)",
            fill=TEXT_DIM, font=("Segoe UI", 10), justify="center"
        )

        # Legenda
        leg = tk.Frame(parent, bg=BG_DARKEST)
        leg.pack(anchor="w", padx=4, pady=(4, 0))
        for color, label in [("#4040ff", "Raro"), ("#00cc88", "Moderado"),
                              ("#ffcc00", "Frequente"), ("#ff2020", "Muito frequente")]:
            tk.Label(leg, text="■", font=("Segoe UI", 10),
                     bg=BG_DARKEST, fg=color).pack(side=tk.LEFT)
            tk.Label(leg, text=f" {label}  ", font=("Segoe UI", 8),
                     bg=BG_DARKEST, fg=TEXT_DIM).pack(side=tk.LEFT)

    # ─────────────────────────────────────────────────────────────────
    #  ASSETS
    # ─────────────────────────────────────────────────────────────────

    def _load_champion_icons(self):
        champs = {s["champion"] for _, s in self.summaries if s and s.get("champion")}
        for name in champs:
            try:
                img = self.map_viz._download_champion_icon(name)
                if img:
                    small = img.resize((MATCH_ICON_SZ, MATCH_ICON_SZ), Image.LANCZOS)
                    self._champ_icons[name] = ImageTk.PhotoImage(small)
            except Exception as e:
                logger.debug(f"Icone do campeão '{name}' não carregado: {e}")

    # ─────────────────────────────────────────────────────────────────
    #  HISTÓRICO DE PARTIDAS (clicável)
    # ─────────────────────────────────────────────────────────────────

    def _render_match_history(self):
        for match_id, s in self.summaries:
            if not s:
                continue
            win  = s.get("win", False)
            chmp = s.get("champion", "?")
            kda  = s.get("kda", "0/0/0")
            cs   = s.get("cs", 0)
            dur  = s.get("duration", "?")
            pos  = s.get("position", "?")
            mode = s.get("mode", "CLASSIC")

            row_bg = ROW_WIN if win else ROW_LOSS

            # Container externo: serve como borda colorida quando selecionado
            container = tk.Frame(self._hist_frame, bg=BG_DARKEST, pady=0)
            container.pack(fill=tk.X, pady=1)

            # Linha interna
            row = tk.Frame(container, bg=row_bg, pady=2)
            row.pack(fill=tk.X, padx=1)  # padx=1 expõe o container → borda

            # Badge V/D
            badge_bg = SUCCESS if win else DANGER
            tk.Label(row, text="V" if win else "D",
                     font=("Segoe UI", 9, "bold"),
                     bg=badge_bg, fg=TEXT_BRIGHT, width=2
                     ).pack(side=tk.LEFT, padx=(4, 3), pady=3)

            # Ícone do campeão
            icon_ph = self._champ_icons.get(chmp)
            if icon_ph:
                lbl = tk.Label(row, image=icon_ph, bg=row_bg)
                lbl.image = icon_ph
                lbl.pack(side=tk.LEFT, padx=(0, 4))
            else:
                tk.Label(row, text=chmp[:8], font=("Segoe UI", 8, "bold"),
                         bg=row_bg, fg=TEXT_COLOR, width=8).pack(side=tk.LEFT, padx=4)

            # KDA
            tk.Label(row, text=kda, font=("Segoe UI", 9, "bold"),
                     bg=row_bg, fg=TEXT_BRIGHT, width=9
                     ).pack(side=tk.LEFT, padx=(2, 4))

            # CS + duração
            tk.Label(row, text=f"{cs}cs", font=("Segoe UI", 8),
                     bg=row_bg, fg=TEXT_DIM, width=5).pack(side=tk.LEFT)
            tk.Label(row, text=dur, font=("Segoe UI", 8),
                     bg=row_bg, fg=TEXT_DIM, width=6).pack(side=tk.LEFT)

            # Posição
            pos_short = {"JUNGLE": "JGL", "BOTTOM": "ADC", "UTILITY": "SUP",
                         "TOP": "TOP", "MIDDLE": "MID"}.get(pos, pos[:3] if pos else "?")
            tk.Label(row, text=pos_short, font=("Segoe UI", 8),
                     bg=row_bg, fg=ACCENT, width=4).pack(side=tk.LEFT)

            # Modo
            mode_short = {"CLASSIC": "SR", "ARAM": "ARAM", "URF": "URF"}.get(mode, mode[:4])
            tk.Label(row, text=mode_short, font=("Segoe UI", 8),
                     bg=row_bg, fg=TEXT_DIM, width=4).pack(side=tk.LEFT)

            # Indicador de status de loading (● = pronto, ○ = aguardando)
            status_lbl = tk.Label(row, text="○", font=("Segoe UI", 9),
                                  bg=row_bg, fg=TEXT_DIM)
            status_lbl.pack(side=tk.RIGHT, padx=6)

            # Guarda referências
            self._match_rows[match_id] = (container, row, row_bg, status_lbl)

            # Bind de clique em todos os widgets da linha
            click_cb = lambda e, mid=match_id: self._on_match_click(mid)
            for widget in [container, row] + list(row.winfo_children()):
                widget.bind("<Button-1>", click_cb)
                widget.config(cursor="hand2")

    # ─────────────────────────────────────────────────────────────────
    #  SELEÇÃO DE PARTIDA
    # ─────────────────────────────────────────────────────────────────

    def _on_match_click(self, match_id: str):
        """Seleciona / desseleciona uma partida e atualiza o heatmap."""
        # Clicar na mesma = desseleciona (volta para "todas")
        new_sel = None if self._selected_id == match_id else match_id
        self._selected_id = new_sel

        # Atualiza highlight de todas as linhas
        for mid, (container, row, row_bg, _) in self._match_rows.items():
            if mid == new_sel:
                container.config(bg=ACCENT)
                row.config(bg=ROW_SEL)
                for w in row.winfo_children():
                    try:
                        w.config(bg=ROW_SEL)
                    except tk.TclError:
                        pass
            else:
                container.config(bg=BG_DARKEST)
                row.config(bg=row_bg)
                for w in row.winfo_children():
                    try:
                        w.config(bg=row_bg)
                    except tk.TclError:
                        pass

        # Atualiza subtítulo
        if new_sel is None:
            self._heatmap_subtitle.config(text="Todas as partidas", fg=ACCENT)
        else:
            s = next((s for mid, s in self.summaries if mid == new_sel), None)
            chmp = s.get("champion", "?") if s else "?"
            kda  = s.get("kda", "?") if s else "?"
            dur  = s.get("duration", "?") if s else "?"
            self._heatmap_subtitle.config(
                text=f"{chmp}  •  {kda}  •  {dur}",
                fg=WARNING
            )

        # Exibe heatmap da partida selecionada (se disponível)
        self._refresh_heatmap()

    # ─────────────────────────────────────────────────────────────────
    #  TOP CAMPEÕES
    # ─────────────────────────────────────────────────────────────────

    def _render_champion_stats(self):
        stats: dict[str, dict] = {}
        for _, s in self.summaries:
            if not s or not s.get("champion"):
                continue
            c = s["champion"]
            if c not in stats:
                stats[c] = {"wins": 0, "games": 0, "kills": 0, "deaths": 0, "assists": 0}
            stats[c]["games"] += 1
            if s.get("win"):
                stats[c]["wins"] += 1
            try:
                k, d, a = (int(x) for x in s.get("kda", "0/0/0").split("/"))
                stats[c]["kills"]   += k
                stats[c]["deaths"]  += d
                stats[c]["assists"] += a
            except ValueError:
                pass

        all_champs = sorted(stats.items(), key=lambda x: x[1]["games"], reverse=True)

        for champ_name, cst in all_champs:
            games = cst["games"]
            wins  = cst["wins"]
            wr    = int(wins / games * 100) if games else 0
            kda_v = (cst["kills"] + cst["assists"]) / max(cst["deaths"], 1)
            wr_fg = SUCCESS if wr >= 50 else DANGER

            row = tk.Frame(self._champ_frame, bg=BG_MEDIUM, pady=5)
            row.pack(fill=tk.X, pady=1)

            icon_ph = self._champ_icons.get(champ_name)
            if icon_ph:
                lbl = tk.Label(row, image=icon_ph, bg=BG_MEDIUM)
                lbl.image = icon_ph
                lbl.pack(side=tk.LEFT, padx=(6, 6))

            info = tk.Frame(row, bg=BG_MEDIUM)
            info.pack(side=tk.LEFT, fill=tk.X, expand=True)
            tk.Label(info, text=champ_name, font=("Segoe UI", 9, "bold"),
                     bg=BG_MEDIUM, fg=TEXT_BRIGHT).pack(anchor="w")
            tk.Label(info, text=f"{games} partida{'s' if games > 1 else ''}  •  KDA {kda_v:.1f}",
                     font=("Segoe UI", 8), bg=BG_MEDIUM, fg=TEXT_DIM).pack(anchor="w")

            bar_outer = tk.Frame(row, bg=BG_LIGHT, width=110, height=8)
            bar_outer.pack(side=tk.LEFT, padx=(0, 6))
            bar_outer.pack_propagate(False)
            tk.Frame(bar_outer, bg=wr_fg, width=int(110 * wr / 100), height=8).place(x=0, y=0)

            tk.Label(row, text=f"{wr}%", font=("Segoe UI", 9, "bold"),
                     bg=BG_MEDIUM, fg=wr_fg, width=4).pack(side=tk.LEFT, padx=(0, 6))

    # ─────────────────────────────────────────────────────────────────
    #  HEATMAP — thread de background
    # ─────────────────────────────────────────────────────────────────

    def _start_heatmap_thread(self):
        if not HAS_NUMPY:
            self._set_loading_text("NumPy não instalado.\npip install numpy")
            return
        threading.Thread(target=self._heatmap_thread, daemon=True).start()

    def _heatmap_thread(self):
        """Baixa minimap + timelines, computa densidade por partida no bg."""
        # Baixa minimap uma vez
        try:
            minimap = self.map_viz._download_minimap()
        except Exception as e:
            logger.warning(f"Falha ao baixar minimap: {e}")
            minimap = None
        self.root.after(0, self._set_minimap, minimap)

        total = len(self.summaries)
        for i, (match_id, _) in enumerate(self.summaries):
            if self._closed:
                return

            self.root.after(0, self._set_loading_text,
                            f"Baixando timeline {i + 1}/{total}…")
            try:
                timeline = self.match_api.get_match_timeline(match_id)
                if not timeline:
                    continue

                md = self.cache.get(match_id)
                if not md:
                    continue
                pid_str = self._find_pid_str(md)
                if pid_str is None:
                    continue

                density = self._compute_density(timeline, pid_str)
                # Envia para thread principal processar
                self.root.after(0, self._on_match_loaded, match_id, density)
            except Exception as e:
                logger.warning(f"Falha ao processar timeline {match_id}: {e}")
                continue

    def _compute_density(self, timeline, pid_str: str) -> "np.ndarray":
        """Acumula posições do jogador no grid do heatmap."""
        density = np.zeros((HEATMAP_SIZE, HEATMAP_SIZE), dtype=np.float32)
        frames = timeline.get("info", {}).get("frames", [])
        for frame in frames:
            pos = (frame.get("participantFrames", {})
                   .get(pid_str, {})
                   .get("position", {}))
            gx = pos.get("x", 0)
            gy = pos.get("y", 0)
            if gx == 0 and gy == 0:
                continue
            cx, cy = self._game_to_canvas(gx, gy)
            if 0 <= cx < HEATMAP_SIZE and 0 <= cy < HEATMAP_SIZE:
                density[cy, cx] += 1.0
        return density

    # ─────────────────────────────────────────────────────────────────
    #  CALLBACKS NA THREAD PRINCIPAL
    # ─────────────────────────────────────────────────────────────────

    def _set_minimap(self, minimap: Image.Image | None):
        self._minimap = minimap

    def _on_match_loaded(self, match_id: str, density: "np.ndarray"):
        """Chamado na thread principal quando uma timeline foi processada."""
        if self._closed:
            return
        self._match_densities[match_id] = density

        # Acumula no total
        if self._total_density is None:
            self._total_density = density.copy()
        else:
            self._total_density += density

        # Marca a linha como pronta (● verde)
        row_info = self._match_rows.get(match_id)
        if row_info:
            _, _, _, status_lbl = row_info
            try:
                status_lbl.config(text="●", fg=SUCCESS)
            except tk.TclError:
                pass

        # Atualiza heatmap se for a partida selecionada ou "todas"
        if self._selected_id is None or self._selected_id == match_id:
            self._refresh_heatmap()

    def _refresh_heatmap(self):
        """Renderiza e exibe o heatmap da seleção atual."""
        if self._closed:
            return

        if self._selected_id is not None:
            density = self._match_densities.get(self._selected_id)
            if density is None:
                # Ainda não carregou — mostra mensagem
                self._set_loading_text(
                    f"Aguardando timeline…\n({self._selected_id})"
                )
                return
        else:
            density = self._total_density
            if density is None:
                return  # nenhuma timeline carregada ainda

        img = self._build_heatmap_image(density, self._minimap)
        ph  = ImageTk.PhotoImage(img)
        self._heatmap_ph = ph
        self._heatmap_canvas.delete("all")
        self._heatmap_canvas.create_image(0, 0, anchor="nw", image=ph)

    # ─────────────────────────────────────────────────────────────────
    #  PROCESSAMENTO DA IMAGEM
    # ─────────────────────────────────────────────────────────────────

    def _find_pid_str(self, match_data) -> str | None:
        for p in match_data.get("info", {}).get("participants", []):
            if p.get("puuid") == self.puuid:
                return str(p.get("participantId"))
        return None

    def _game_to_canvas(self, gx, gy) -> tuple[int, int]:
        cx = int((gx - MAP_MIN_X) / (MAP_MAX_X - MAP_MIN_X) * HEATMAP_SIZE)
        cy = int((1.0 - (gy - MAP_MIN_Y) / (MAP_MAX_Y - MAP_MIN_Y)) * HEATMAP_SIZE)
        return cx, cy

    def _build_heatmap_image(self, density: "np.ndarray",
                             minimap: Image.Image | None) -> Image.Image:
        """Minimap + overlay estilo Google Maps: blobs grandes e saturados."""
        max_v = density.max()
        if max_v <= 0:
            max_v = 1.0
        norm = density / max_v

        # Gaussian blur via FFT — opera em float64, sem truncamento uint8.
        # PIL GaussianBlur trunca valores <1 quando radius é grande,
        # fazendo blobs esparsos desaparecerem completamente.
        # σ=22 px ≈ blobs de ~66px de diâmetro visível (estilo Google Maps).
        norm_blur = _gaussian_blur_fft(norm, sigma=22)

        # Re-normaliza para pico = 1.0
        peak = norm_blur.max()
        if peak > 0:
            norm_blur /= peak

        rgba    = _gmaps_colormap(norm_blur.astype(np.float32))
        overlay = Image.fromarray(rgba, mode="RGBA")

        if minimap:
            base = minimap.resize((HEATMAP_SIZE, HEATMAP_SIZE), Image.LANCZOS).convert("RGBA")
        else:
            base = Image.new("RGBA", (HEATMAP_SIZE, HEATMAP_SIZE), (20, 28, 38, 255))

        return Image.alpha_composite(base, overlay).convert("RGB")

    # ─────────────────────────────────────────────────────────────────
    #  HELPERS DE UI
    # ─────────────────────────────────────────────────────────────────

    def _set_loading_text(self, text: str):
        if self._closed:
            return
        try:
            self._heatmap_canvas.itemconfigure(self._loading_id, text=text)
        except tk.TclError:
            pass

    def _on_close(self):
        self._closed = True
        self.win.destroy()


# ═══════════════════════════════════════════════════════════════════════
#  FUNÇÕES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════

def _section_label(parent, text: str):
    tk.Label(parent, text=text, font=("Segoe UI", 9, "bold"),
             bg=BG_DARKEST, fg=TEXT_DIM).pack(anchor="w", padx=4, pady=(4, 2))


def _gaussian_blur_fft(arr: "np.ndarray", sigma: float) -> "np.ndarray":
    """Gaussian blur via FFT — float64, sem dependência de scipy.

    Equivalente a scipy.ndimage.gaussian_filter mas usando apenas numpy.
    Vantagem: sem truncamento uint8 → funciona corretamente com raios grandes.

    sigma: desvio padrão em pixels (σ=22 → blob visível de ~66px de diâmetro)
    """
    h, w   = arr.shape
    ky     = np.fft.fftfreq(h)          # freq em ciclos/pixel, eixo Y
    kx     = np.fft.fftfreq(w)          # freq em ciclos/pixel, eixo X
    Kx, Ky = np.meshgrid(kx, ky)
    # Gaussian 2D no domínio da frequência (fechado analiticamente)
    gauss  = np.exp(-2.0 * np.pi ** 2 * sigma ** 2 * (Kx ** 2 + Ky ** 2))
    blurred = np.real(np.fft.ifft2(np.fft.fft2(arr.astype(np.float64)) * gauss))
    return blurred.astype(np.float32)


def _gmaps_colormap(norm: "np.ndarray") -> "np.ndarray":
    """Colormap estilo Google Maps: azul→ciano→verde→amarelo→laranja→vermelho.

    Características:
    - 6 segmentos de cor para gradiente mais rico
    - Alpha opaco mesmo em baixa densidade (borda azul sempre visível)
    - Hotspots vermelhos saturados no centro
    """
    v    = norm
    h, w = v.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)

    # Alpha: linear após threshold; bordas já têm opacidade razoável
    # Áreas com v < 0.04 ficam transparentes (fundo do mapa aparece limpo)
    thr   = 0.04
    alpha = np.where(v > thr,
                     np.clip((v - thr) / (1.0 - thr) * 230 + 25, 25, 230),
                     0)
    rgba[:, :, 3] = alpha.astype(np.uint8)

    def seg(lo, hi, r0, g0, b0, r1, g1, b1):
        """Interpola linearmente um segmento de cor."""
        m = (v >= lo) & (v < hi)
        t = np.where(m, (v - lo) / (hi - lo), 0.0)
        rgba[:, :, 0] = np.where(m, (r0 + t * (r1 - r0)).astype(np.uint8), rgba[:, :, 0])
        rgba[:, :, 1] = np.where(m, (g0 + t * (g1 - g0)).astype(np.uint8), rgba[:, :, 1])
        rgba[:, :, 2] = np.where(m, (b0 + t * (b1 - b0)).astype(np.uint8), rgba[:, :, 2])

    # azul escuro → azul puro       (0.00–0.18)
    seg(0.00, 0.18,    0,   0, 128,    0,   0, 255)
    # azul → ciano                  (0.18–0.35)
    seg(0.18, 0.35,    0,   0, 255,    0, 255, 255)
    # ciano → verde                 (0.35–0.52)
    seg(0.35, 0.52,    0, 255, 255,    0, 255,   0)
    # verde → amarelo               (0.52–0.68)
    seg(0.52, 0.68,    0, 255,   0,  255, 255,   0)
    # amarelo → laranja             (0.68–0.83)
    seg(0.68, 0.83,  255, 255,   0,  255, 120,   0)
    # laranja → vermelho intenso    (0.83–1.00)
    seg(0.83, 1.01,  255, 120,   0,  200,   0,   0)

    return rgba
