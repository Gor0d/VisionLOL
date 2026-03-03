#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gera docs/screenshots/Scrims.png — mockup do Scrims Dashboard (paiN vs FURIA)."""

from PIL import Image, ImageDraw, ImageFont
import math, os

# ── Dimensões ────────────────────────────────────────────────────────
W, H      = 1120, 700
LEFT_W    = 310
HDR_H     = 58
PAD       = 10

# ── Paleta ───────────────────────────────────────────────────────────
BG_DARKEST  = (13,  17,  23)
BG_DARK     = (22,  27,  34)
BG_MEDIUM   = (28,  33,  41)
BG_LIGHT    = (33,  38,  45)
BORDER      = (48,  54,  61)
ACCENT      = (88, 166, 255)
SUCCESS     = (63, 185,  80)
DANGER      = (248, 81,  73)
WARNING     = (210, 153,  34)
PAIN_BLUE   = (0,   91, 172)
PAIN_GOLD   = (245, 166,  35)
TEXT_BRIGHT = (255, 255, 255)
TEXT_COLOR  = (230, 237, 243)
TEXT_DIM    = (125, 133, 144)
ROW_WIN     = (15,  42,  20)
ROW_LOSS    = (42,  15,  15)
ROW_SEL     = (26,  58,  95)
ROLE_TOP    = (255, 100,  50)
ROLE_JUN    = (50,  200,  80)
ROLE_MID    = (100, 150, 255)
ROLE_ADC    = (255, 215,   0)
ROLE_SUP    = (180, 100, 255)


def _c(hex_str: str):
    h = hex_str.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


# ── Fontes ───────────────────────────────────────────────────────────
FONT_DIR = "C:/Windows/Fonts"

def _font(size: int, bold=False):
    try:
        name = "segoeuib.ttf" if bold else "segoeui.ttf"
        return ImageFont.truetype(os.path.join(FONT_DIR, name), size)
    except Exception:
        return ImageFont.load_default()


F7  = _font(7)
F8  = _font(8)
F8B = _font(8,  bold=True)
F9B = _font(9,  bold=True)
F10 = _font(10)
F10B= _font(10, bold=True)
F11B= _font(11, bold=True)
F13B= _font(13, bold=True)
F16B= _font(16, bold=True)
F18 = _font(18)


# ── Helpers de desenho ───────────────────────────────────────────────

def rect(d: ImageDraw.ImageDraw, xy, fill=None, outline=None, radius=0):
    if radius:
        d.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)
    else:
        d.rectangle(xy, fill=fill, outline=outline)


def text(d: ImageDraw.ImageDraw, pos, txt, font, fill=TEXT_COLOR, anchor="lt"):
    d.text(pos, txt, font=font, fill=fill, anchor=anchor)


def badge(d, x, y, label, bg, fg=BG_DARKEST, font=F8B, w=38, h=16):
    rect(d, [x, y, x + w, y + h], fill=bg, radius=3)
    cx = x + w // 2
    cy = y + h // 2
    d.text((cx, cy), label, font=font, fill=fg, anchor="mm")


# ── Mini-radar ───────────────────────────────────────────────────────

def mini_radar(d: ImageDraw.ImageDraw, cx, cy, R, values: list, color):
    n   = len(values)
    ang = [-math.pi / 2 + 2 * math.pi * i / n for i in range(n)]

    # Fundo
    for level in [0.5, 1.0]:
        pts = []
        for a in ang:
            pts.append((cx + R * level * math.cos(a),
                        cy + R * level * math.sin(a)))
        d.polygon(pts,
                  outline=BORDER if level == 1 else (30, 38, 48),
                  fill=None)

    for a in ang:
        d.line([(cx, cy), (cx + R * math.cos(a), cy + R * math.sin(a))],
               fill=(30, 38, 48), width=1)

    # Polígono dos valores
    pts = []
    for i, v in enumerate(values):
        pts.append((cx + R * v * math.cos(ang[i]),
                    cy + R * v * math.sin(ang[i])))

    fill_r = tuple(int(color[j] * 0.3 + BG_DARK[j] * 0.7) for j in range(3))
    d.polygon(pts, fill=fill_r, outline=color)

    for px, py in pts:
        d.ellipse([px - 3, py - 3, px + 3, py + 3], fill=color, outline=BG_DARKEST)


# ── Barra de métrica ─────────────────────────────────────────────────

def metric_bar(d, x, y, label, value_str, pct, bar_color, ref_str):
    # Label
    d.text((x, y + 1), label, font=F8, fill=TEXT_DIM)
    # Valor
    d.text((x + 112, y + 1), value_str, font=F8B, fill=bar_color, anchor="rt")
    # Barra de fundo
    bx = x + 116
    rect(d, [bx, y + 3, bx + 170, y + 10], fill=BG_LIGHT)
    # Preenchimento
    fw = int(170 * min(max(pct, 0), 1))
    if fw > 0:
        rect(d, [bx, y + 3, bx + fw, y + 10], fill=bar_color)
    # Ref
    d.text((bx + 175, y + 1), f"ref {ref_str}", font=F7, fill=TEXT_DIM)


# ════════════════════════════════════════════════════════════════════
#  GERAÇÃO PRINCIPAL
# ════════════════════════════════════════════════════════════════════

img = Image.new("RGB", (W, H), BG_DARKEST)
d   = ImageDraw.Draw(img)

# ── Borda externa ────────────────────────────────────────────────────
rect(d, [PAD, PAD, W - PAD, H - PAD], outline=BORDER)

# ════════════════════════════════════════════════════════════════════
#  HEADER
# ════════════════════════════════════════════════════════════════════
hx1, hy1, hx2, hy2 = PAD, PAD, W - PAD, PAD + HDR_H
rect(d, [hx1, hy1, hx2, hy2], fill=PAIN_BLUE)

# Ícone + título
d.text((28, 25), "⚔", font=F18, fill=PAIN_GOLD)
d.text((58, 20), "Scrims",     font=F16B, fill=PAIN_GOLD)
d.text((118, 20), " Dashboard", font=F16B, fill=TEXT_BRIGHT)

# Stats
stats_txt = "2 sessões  ·  5 jogos  ·  2 adversários"
d.text((W - PAD - 20, 33), stats_txt, font=F10, fill=(168, 196, 224), anchor="rm")

# Botão
btn_x = W - PAD - 160
rect(d, [btn_x, 22, btn_x + 120, 46], fill=(26, 95, 63), radius=4)
d.text((btn_x + 60, 34), "＋ Nova Sessão", font=F9B, fill=TEXT_COLOR, anchor="mm")

# ════════════════════════════════════════════════════════════════════
#  PAINEL ESQUERDO — lista de sessões
# ════════════════════════════════════════════════════════════════════
LX = PAD
RX = PAD + LEFT_W
TY = PAD + HDR_H + 6

# Título da seção
d.text((LX + 6, TY + 6), "SESSÕES DE SCRIM", font=F9B, fill=TEXT_DIM)

# ── Sessão 1: FURIA (selecionada) ───────────────────────────────────
sy = TY + 28
rect(d, [LX + 2, sy,     RX - 2, sy + 40], fill=ROW_SEL)
rect(d, [LX,     sy,     LX + 2, sy + 40], fill=ACCENT)  # borda de seleção
d.text((LX + 8,  sy + 6),  "2025-03-01",  font=F8,  fill=TEXT_DIM)
d.text((LX + 90, sy + 5),  "vs  FURIA",   font=F10B, fill=DANGER)
d.text((LX + 200, sy + 6), "3 jogos",     font=F8,  fill=TEXT_DIM)
d.text((LX + 8,  sy + 22), "· BO3 treino pré-CBLOL", font=_font(8, False), fill=TEXT_DIM)

# ── Sessão 2: RED Canids ─────────────────────────────────────────────
sy2 = sy + 46
rect(d, [LX + 2, sy2, RX - 2, sy2 + 40], fill=BG_MEDIUM)
d.text((LX + 8,  sy2 + 6),  "2025-02-28",   font=F8,  fill=TEXT_DIM)
d.text((LX + 90, sy2 + 5),  "vs  RED Canids", font=F10B, fill=DANGER)
d.text((LX + 210, sy2 + 6), "2 jogos",      font=F8,  fill=TEXT_DIM)
d.text((LX + 8,  sy2 + 22), "· Fase de grupos", font=F8, fill=TEXT_DIM)

# Separador vertical
rect(d, [RX + 2, PAD + HDR_H, RX + 2, H - PAD], fill=BORDER)

# ════════════════════════════════════════════════════════════════════
#  PAINEL DIREITO — detalhe da sessão FURIA
# ════════════════════════════════════════════════════════════════════
DX = RX + 8   # x início painel direito
DW = W - PAD - DX  # largura

# ── Cabeçalho da sessão ──────────────────────────────────────────────
dh_y = PAD + HDR_H + 6
rect(d, [DX, dh_y, W - PAD, dh_y + 44], fill=BG_DARK)
d.text((DX + 14, dh_y + 12), "⚔  vs FURIA", font=F13B, fill=DANGER)
d.text((DX + 160, dh_y + 15), "2025-03-01", font=F10, fill=TEXT_DIM)
d.text((DX + 260, dh_y + 15), "· BO3 treino pré-CBLOL", font=_font(9, False), fill=TEXT_DIM)
d.text((W - PAD - 14, dh_y + 15), "3 partidas", font=F10, fill=ACCENT, anchor="rm")

# ── Título tabela ────────────────────────────────────────────────────
sec_y = dh_y + 52
d.text((DX + 4, sec_y), "PARTIDAS DA SESSÃO", font=F9B, fill=TEXT_DIM)

# Cabeçalho da tabela
th_y = sec_y + 18
rect(d, [DX, th_y, W - PAD, th_y + 22], fill=BG_MEDIUM)
for txt_h, ox in [("Partida", 0), ("Duração", 130), ("Resultado", 195), ("Campeões (Nosso Time)", 280)]:
    d.text((DX + ox + 4, th_y + 5), txt_h, font=F8B, fill=TEXT_DIM)

# Rows das partidas
matches = [
    ("…3213218969", "32:14", True,  "Garen(TOP)  Khazix(JGL)  Akali(MID)  Jinx(BOT)  Thresh(SUP)"),
    ("…3213236913", "28:07", True,  "Darius(TOP)  Vi(JGL)  Orianna(MID)  Caitlyn(BOT)  Lulu(SUP)"),
    ("…3213256103", "41:53", False, "Camille(TOP)  Hecarim(JGL)  Azir(MID)  Aphelios(BOT)  Naut(SUP)"),
]
row_y = th_y + 24
for mid_s, dur, won, champs in matches:
    bg = ROW_WIN if won else ROW_LOSS
    rect(d, [DX, row_y, W - PAD, row_y + 20], fill=bg)
    d.text((DX + 4,   row_y + 4), mid_s, font=F8, fill=TEXT_DIM)
    d.text((DX + 134, row_y + 4), dur,   font=F8, fill=TEXT_COLOR)
    result_col = SUCCESS if won else DANGER
    result_txt = "✓ Vitória" if won else "✕ Derrota"
    d.text((DX + 199, row_y + 4), result_txt, font=F8B, fill=result_col)
    d.text((DX + 284, row_y + 4), champs, font=F8, fill=TEXT_COLOR)
    row_y += 22

# ── Separador ────────────────────────────────────────────────────────
sep_y = row_y + 4
rect(d, [DX, sep_y, W - PAD, sep_y + 1], fill=BORDER)

# ── Título performance ───────────────────────────────────────────────
perf_y = sep_y + 8
d.text((DX + 4, perf_y), "PERFORMANCE POR JOGADOR — NESTA SESSÃO", font=F9B, fill=TEXT_DIM)

# ══════════════════════════════════════════════
#  Card: Robo (TOP)
# ══════════════════════════════════════════════
card_y = perf_y + 18
card_h = 108
rect(d, [DX, card_y, W - PAD, card_y + card_h], fill=BG_DARK)
# Barra lateral de role
rect(d, [DX, card_y, DX + 4, card_y + card_h], fill=ROLE_TOP)

# Cabeçalho do card
badge(d, DX + 8, card_y + 8, "TOP", ROLE_TOP)
d.text((DX + 52, card_y + 7),  "Robo",      font=F11B, fill=TEXT_BRIGHT)
d.text((DX + 110, card_y + 9), "  3 partidas", font=F8, fill=TEXT_DIM)

# Botão radar
br_x = W - PAD - 90
rect(d, [br_x, card_y + 7, br_x + 82, card_y + 23], fill=BG_LIGHT, radius=3)
d.text((br_x + 41, card_y + 15), "🕸 Ver Radar", font=F8B, fill=ACCENT, anchor="mm")

# Mini-radar Robo
radar_cx = DX + 68
radar_cy = card_y + 68
mini_radar(d, radar_cx, radar_cy, 42,
           [0.72, 0.58, 0.80, 0.65, 0.55, 0.70], ROLE_TOP)

# Barras de métricas Robo
metrics_robo = [
    ("⚔ KDA",        "3.2",  0.72, SUCCESS,  "3.0"),
    ("🌾 CS/min",     "7.8",  0.58, WARNING,  "8.0"),
    ("👁 Visão/min",  "0.41", 0.80, SUCCESS,  "0.35"),
    ("💰 Gold/min",   "412",  0.65, WARNING,  "420"),
    ("💥 Dmg Share",  "28%",  0.55, WARNING,  "25%"),
    ("🤝 Kill Part.", "71%",  0.70, SUCCESS,  "65%"),
]
mx = DX + 148
my = card_y + 14
for label, val, pct, col, ref in metrics_robo:
    bar_col = SUCCESS if pct >= 0.85 else (WARNING if pct >= 0.60 else DANGER)
    metric_bar(d, mx, my, label, val, pct, bar_col, ref)
    my += 14

# ══════════════════════════════════════════════
#  Card: PNG Caca (JGL)
# ══════════════════════════════════════════════
card2_y = card_y + card_h + 4
card2_h = 108
rect(d, [DX, card2_y, W - PAD, card2_y + card2_h], fill=BG_DARK)
rect(d, [DX, card2_y, DX + 4, card2_y + card2_h], fill=ROLE_JUN)

badge(d, DX + 8, card2_y + 8, "JGL", ROLE_JUN)
d.text((DX + 52, card2_y + 7),  "PNG Caca",  font=F11B, fill=TEXT_BRIGHT)
d.text((DX + 140, card2_y + 9), "  3 partidas", font=F8, fill=TEXT_DIM)

br2_x = W - PAD - 90
rect(d, [br2_x, card2_y + 7, br2_x + 82, card2_y + 23], fill=BG_LIGHT, radius=3)
d.text((br2_x + 41, card2_y + 15), "🕸 Ver Radar", font=F8B, fill=ACCENT, anchor="mm")

radar2_cx = DX + 68
radar2_cy = card2_y + 68
mini_radar(d, radar2_cx, radar2_cy, 42,
           [0.60, 0.91, 0.55, 0.78, 0.88, 0.82], ROLE_JUN)

metrics_caca = [
    ("⚔ KDA",        "4.1",  0.60, WARNING,  "4.5"),
    ("🌾 CS/min",     "5.9",  0.91, SUCCESS,  "5.5"),
    ("👁 Visão/min",  "0.38", 0.55, WARNING,  "0.45"),
    ("💰 Gold/min",   "398",  0.78, SUCCESS,  "380"),
    ("💥 Dmg Share",  "19%",  0.88, SUCCESS,  "18%"),
    ("🤝 Kill Part.", "82%",  0.82, SUCCESS,  "72%"),
]
mx2 = DX + 148
my2 = card2_y + 14
for label, val, pct, col, ref in metrics_caca:
    bar_col = SUCCESS if pct >= 0.85 else (WARNING if pct >= 0.60 else DANGER)
    metric_bar(d, mx2, my2, label, val, pct, bar_col, ref)
    my2 += 14

# ── Salva ────────────────────────────────────────────────────────────
out = os.path.join(os.path.dirname(__file__), "screenshots", "Scrims.png")
img.save(out, "PNG")
print(f"Mockup salvo em: {out}")
