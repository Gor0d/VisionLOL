# -*- coding: utf-8 -*-
"""
Geração de relatório mensal de progresso em HTML.
Abre automaticamente no browser padrão — sem dependência de weasyprint.
"""

import os
import json
import webbrowser
from datetime import datetime, date
from typing import List

from ..models.player  import Player
from ..models.session import CoachingSession
from ..models.goal    import SmartGoal, METRIC_LABELS

_TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               "templates", "report_template.html")
_REPORTS_DIR   = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                               "coaching_data", "reports")


def generate_monthly_report(
    player: Player,
    sessions: List[CoachingSession],
    month: int,
    year: int,
    current_metrics: dict | None = None,
) -> str:
    """
    Gera relatório HTML mensal.
    Retorna o caminho do arquivo gerado.
    """
    os.makedirs(_REPORTS_DIR, exist_ok=True)

    # Filtra sessões do mês
    month_sessions = [
        s for s in sessions
        if s.date[:7] == f"{year}-{month:02d}"
    ]

    # Métricas baseline vs atual
    baseline = player.baseline_metrics or {}
    current  = current_metrics or {}

    metric_rows = []
    for metric, label in METRIC_LABELS.items():
        base = baseline.get(metric)
        curr = current.get(metric)
        if base is None and curr is None:
            continue
        delta = (curr - base) if (base is not None and curr is not None) else None
        metric_rows.append({
            "label": label,
            "base":  f"{base:.2f}" if base is not None else "—",
            "curr":  f"{curr:.2f}" if curr is not None else "—",
            "delta": f"{delta:+.2f}" if delta is not None else "—",
            "up":    delta > 0 if delta is not None else None,
        })

    # Metas do jogador
    goal_rows = []
    for g_dict in player.goals:
        goal = SmartGoal.from_dict(g_dict)
        curr_val = current.get(goal.metric, goal.current_value)
        prog     = goal.check_progress(curr_val)
        goal_rows.append({
            "label":    goal.metric_label,
            "target":   f"{goal.target_value:.2f}",
            "current":  f"{curr_val:.2f}",
            "pct":      f"{prog['pct']:.0f}",
            "status":   goal.status,
            "deadline": goal.deadline[:10],
        })

    # Próximos passos: dos homeworks das sessões do mês
    next_steps = []
    for s in month_sessions:
        next_steps.extend(s.homework)
    next_steps = list(dict.fromkeys(next_steps))[:6]  # deduplica, max 6

    # Renderiza HTML
    html = _render_template(
        player        = player,
        month         = month,
        year          = year,
        month_sessions= month_sessions,
        metric_rows   = metric_rows,
        goal_rows     = goal_rows,
        next_steps    = next_steps,
    )

    filename = f"report_{player.id}_{year}_{month:02d}.html"
    filepath = os.path.join(_REPORTS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    return filepath


def _render_template(player, month, year, month_sessions,
                     metric_rows, goal_rows, next_steps) -> str:
    month_name = datetime(year, month, 1).strftime("%B %Y")

    # Sessions list HTML
    sessions_html = ""
    for s in sorted(month_sessions, key=lambda x: x.date):
        hw_html = "".join(f"<li>{h}</li>" for h in s.homework)
        mistakes_html = "".join(f"<li>{m}</li>" for m in s.key_mistakes)
        mood_stars = "★" * s.checkin_mood + "☆" * (5 - s.checkin_mood)
        sessions_html += f"""
        <div class="session-block">
          <div class="session-header">
            <span class="session-date">{s.date[:10]}</span>
            <span class="session-duration">{s.duration_minutes} min</span>
            <span class="session-mood" title="Humor">{mood_stars}</span>
          </div>
          <p class="checkin">{s.checkin_notes or "—"}</p>
          <div class="two-col">
            <div><strong>Erros:</strong><ul>{mistakes_html or "<li>—</li>"}</ul></div>
            <div><strong>Homework:</strong><ul>{hw_html or "<li>—</li>"}</ul></div>
          </div>
          {f'<p class="drill"><strong>Drill:</strong> {s.drill_performed}</p>' if s.drill_performed else ""}
        </div>"""

    # Metrics table HTML
    metrics_html = ""
    for row in metric_rows:
        color = "green" if row["up"] else ("red" if row["up"] is False else "")
        metrics_html += f"""
        <tr>
          <td>{row["label"]}</td>
          <td>{row["base"]}</td>
          <td>{row["curr"]}</td>
          <td class="{color}">{row["delta"]}</td>
        </tr>"""

    # Goals HTML
    goals_html = ""
    for g in goal_rows:
        status_cls = {"achieved": "achieved", "failed": "failed", "active": "active", "paused": "paused"}.get(g["status"], "")
        goals_html += f"""
        <tr>
          <td>{g["label"]}</td>
          <td>{g["target"]}</td>
          <td>{g["current"]}</td>
          <td>
            <div class="progress-bar"><div class="progress-fill" style="width:{g['pct']}%"></div></div>
            <span class="progress-label">{g["pct"]}%</span>
          </td>
          <td><span class="goal-status {status_cls}">{g["status"].upper()}</span></td>
          <td>{g["deadline"]}</td>
        </tr>"""

    # Next steps HTML
    next_html = "".join(f"<li>{s}</li>" for s in next_steps) or "<li>Sem recomendações registradas</li>"

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Relatório {player.display} — {month_name}</title>
<style>
  :root {{
    --bg: #0a0a0a; --bg2: #111; --bg3: #181818;
    --border: #2a2a2a; --accent: #FF9830; --cyan: #20F0FF;
    --green: #50FF50; --red: #FF4040; --text: #e0e0e0; --dim: #606060;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: 'IBM Plex Mono', 'Courier New', monospace;
          font-size: 13px; padding: 32px; max-width: 960px; margin: 0 auto; }}
  h1 {{ color: var(--accent); font-size: 22px; margin-bottom: 4px; }}
  h2 {{ color: var(--cyan); font-size: 14px; letter-spacing: 0.12em; margin: 28px 0 12px; border-bottom: 1px solid var(--border); padding-bottom: 6px; }}
  .subtitle {{ color: var(--dim); font-size: 11px; margin-bottom: 24px; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 16px; }}
  th {{ padding: 8px 10px; text-align: left; color: var(--dim); font-size: 11px; border-bottom: 1px solid var(--border); }}
  td {{ padding: 7px 10px; border-bottom: 1px solid #111; }}
  tr:hover td {{ background: #0c0c0c; }}
  .green {{ color: var(--green); }} .red {{ color: var(--red); }}
  .session-block {{ background: var(--bg2); border: 1px solid var(--border); border-radius: 4px; padding: 14px; margin-bottom: 12px; }}
  .session-header {{ display: flex; gap: 16px; align-items: center; margin-bottom: 8px; }}
  .session-date {{ color: var(--accent); font-weight: 700; }}
  .session-duration {{ color: var(--dim); font-size: 11px; }}
  .session-mood {{ color: #aa7700; font-size: 12px; }}
  .checkin {{ color: var(--dim); font-size: 12px; margin-bottom: 8px; }}
  .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  .two-col ul {{ margin-left: 16px; font-size: 12px; color: #c0c0c0; margin-top: 4px; }}
  .drill {{ color: var(--cyan); font-size: 12px; margin-top: 8px; }}
  .progress-bar {{ display: inline-block; width: 80px; height: 6px; background: #1a1a1a; border-radius: 3px; vertical-align: middle; }}
  .progress-fill {{ height: 6px; background: var(--accent); border-radius: 3px; }}
  .progress-label {{ margin-left: 6px; color: var(--dim); font-size: 11px; }}
  .goal-status {{ padding: 1px 6px; border-radius: 2px; font-size: 10px; font-weight: 700; }}
  .achieved {{ background: #0a2a0a; color: var(--green); }}
  .failed   {{ background: #2a0a0a; color: var(--red); }}
  .active   {{ background: #1a1200; color: var(--accent); }}
  .paused   {{ background: #1a1a1a; color: var(--dim); }}
  .next-steps {{ background: var(--bg2); border-left: 3px solid var(--cyan); padding: 12px 16px; border-radius: 0 4px 4px 0; }}
  .next-steps ul {{ margin-left: 16px; font-size: 12px; color: #c0c0c0; line-height: 1.9; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 2px; font-size: 10px; font-weight: 700;
            background: #1a0800; color: var(--accent); border: 1px solid #3a1800; }}
  footer {{ margin-top: 40px; color: var(--dim); font-size: 10px; text-align: center; }}
</style>
</head>
<body>

<div style="margin-bottom:4px;font-size:11px;color:var(--dim);">// RELATÓRIO DE PROGRESSO</div>
<h1>◈ {player.display}</h1>
<div class="subtitle">
  <span class="badge">{player.role}</span>
  &nbsp;{player.riot_id}&nbsp;·&nbsp;{month_name}&nbsp;·&nbsp;
  Coaching: {player.coaching_type}&nbsp;·&nbsp;
  {len(month_sessions)} sessão(ões) este mês
</div>

<h2>// MÉTRICAS — INÍCIO VS ATUAL</h2>
<table>
  <thead><tr><th>MÉTRICA</th><th>BASELINE</th><th>ATUAL</th><th>DELTA</th></tr></thead>
  <tbody>{metrics_html or "<tr><td colspan='4' style='color:var(--dim)'>Sem dados de métricas</td></tr>"}</tbody>
</table>

<h2>// SESSÕES DO MÊS</h2>
{sessions_html or "<p style='color:var(--dim);font-size:12px'>Nenhuma sessão registrada neste mês.</p>"}

<h2>// METAS SMART</h2>
<table>
  <thead><tr><th>MÉTRICA</th><th>ALVO</th><th>ATUAL</th><th>PROGRESSO</th><th>STATUS</th><th>PRAZO</th></tr></thead>
  <tbody>{goals_html or "<tr><td colspan='6' style='color:var(--dim)'>Sem metas ativas</td></tr>"}</tbody>
</table>

<h2>// PRÓXIMOS PASSOS</h2>
<div class="next-steps"><ul>{next_html}</ul></div>

<footer>VisionLOL Coaching · Gerado em {datetime.now().strftime("%d/%m/%Y %H:%M")}</footer>

</body>
</html>"""
