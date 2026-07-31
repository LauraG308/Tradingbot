"""
Erzeugt eine eigenständige, mobiloptimierte dashboard.html aus dem aktuellen
Zustand + Verlaufsdaten. Keine externen Abhängigkeiten außer optional
Google Fonts (funktioniert auch offline dank Systemfont-Fallback).
"""

import json
from datetime import datetime
from ticker_names import full_name

HORIZON_LABEL = {"long": "Langfristig", "medium": "Mittelfristig", "short": "Kurzfristig"}


def _sparkline_svg(values: list[float], gain: bool, width=120, height=32) -> str:
    if len(values) < 2:
        return ""
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1
    step = width / (len(values) - 1)
    pts = " ".join(
        f"{i*step:.1f},{height - ((v - lo) / span) * height:.1f}"
        for i, v in enumerate(values)
    )
    color = "#4FB286" if gain else "#D9636B"
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'class="spark"><polyline points="{pts}" fill="none" stroke="{color}" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    )


def render_dashboard(reports_sorted: list[dict], history: dict, swap_history: list[dict],
                      week: int, details: dict | None = None, out_path: str = "dashboard.html"):
    """
    reports_sorted: aktuelle Wochen-Reports, absteigend nach Rendite sortiert
    history: {strategy_id: [portfolio_value, ...]} über alle bisherigen Wochen
    swap_history: Liste der Tausch-Ereignisse (aus state.json)
    details: {strategy_id: {"positions": [...], "trade_log": [...]}} für die
             aufklappbare Detailansicht je Bot
    """
    details = details or {}
    last_swap = swap_history[-1] if swap_history else None

    rows_html = []
    for rank, r in enumerate(reports_sorted, 1):
        gain = r["total_return_pct"] >= 0
        sign = "+" if gain else ""
        vals = history.get(r["strategy_id"], [r["value"]])
        spark = _sparkline_svg(vals, gain)
        just_swapped_in = last_swap and last_swap.get("added") == r["strategy_id"]
        badge = '<span class="tag tag-new">neu eingesetzt</span>' if just_swapped_in else ""

        d = details.get(r["strategy_id"], {})
        positions = [p for p in d.get("positions", []) if p["shares"] > 0]
        trade_log = d.get("trade_log", [])[-15:][::-1]

        if positions:
            pos_rows = "".join(f"""
              <tr>
                <td><div class="asset-name">{full_name(p['ticker'])}</div><div class="asset-ticker">{p['ticker']}</div></td>
                <td>{p['shares']:.4f}</td>
                <td>{p['avg_price']:.2f} €</td>
                <td>{p['current_price']:.2f} €</td>
                <td>{p['market_value']:.2f} €</td>
              </tr>""" for p in positions)
            pos_table = f"""
            <table class="pos-table">
              <thead><tr><th>Wertpapier</th><th>Stück</th><th>Ø Kauf</th><th>Aktuell</th><th>Wert</th></tr></thead>
              <tbody>{pos_rows}</tbody>
            </table>"""
        else:
            pos_table = '<div class="empty-note">Aktuell keine offenen Positionen (nur Cash).</div>'

        if trade_log:
            trade_items = "".join(f'<li>{t}</li>' for t in trade_log)
            trade_html = f'<ul class="trade-log">{trade_items}</ul>'
        else:
            trade_html = '<div class="empty-note">Noch keine Trades in dieser Woche.</div>'

        rows_html.append(f"""
        <details class="row {'gain' if gain else 'loss'}">
          <summary>
            <div class="rank">{rank:02d}</div>
            <div class="info">
              <div class="name-line">
                <span class="name">{r['name']}</span>
                <span class="horizon">{HORIZON_LABEL.get(r['horizon'], r['horizon'])}</span>
                {badge}
              </div>
              <div class="meta">Gebühren: {r['fees_paid']:.2f} € · Cash: {r['cash']:.2f} €</div>
            </div>
            <div class="spark-wrap">{spark}</div>
            <div class="numbers">
              <div class="value">{r['value']:,.0f} €</div>
              <div class="return">{sign}{r['total_return_pct']:.2f}%</div>
            </div>
            <div class="chevron">›</div>
          </summary>
          <div class="detail-panel">
            <h3>Positionen</h3>
            {pos_table}
            <h3>Trades (zuletzt zuerst)</h3>
            {trade_html}
          </div>
        </details>""")

    swap_banner = ""
    if last_swap:
        swap_banner = f"""
        <div class="swap-banner">
          <span class="swap-icon">⇄</span>
          <div>
            <div class="swap-title">Strategie getauscht — Woche {last_swap['week']}</div>
            <div class="swap-detail">„{last_swap['removed']}" abgelöst durch „{last_swap['added']}"</div>
          </div>
        </div>"""

    swap_log_html = "".join(
        f'<li><span class="log-week">W{s["week"]:02d}</span> '
        f'<span class="log-removed">{s["removed"]}</span> → '
        f'<span class="log-added">{s["added"]}</span></li>'
        for s in reversed(swap_history[-8:])
    )

    best = reports_sorted[0]
    worst = reports_sorted[-1]
    total_value = sum(r["value"] for r in reports_sorted)
    total_fees = sum(r["fees_paid"] for r in reports_sorted)

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>Bot A — Kontrollzentrum</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {{
    --ink: #12161C;
    --panel: #1B212B;
    --panel-2: #212836;
    --text: #EDEAE3;
    --muted: #8A93A3;
    --gain: #4FB286;
    --loss: #D9636B;
    --amber: #E3A857;
    --line: #2A3140;
  }}
  * {{ box-sizing: border-box; -webkit-tap-highlight-color: transparent; }}
  html, body {{
    margin: 0; padding: 0; background: var(--ink); color: var(--text);
    font-family: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    -webkit-font-smoothing: antialiased;
  }}
  .wrap {{ max-width: 720px; margin: 0 auto; padding: 20px 16px 48px; }}
  header {{ padding: 8px 4px 20px; }}
  .eyebrow {{
    font-family: 'IBM Plex Mono', monospace; font-size: 12px; letter-spacing: 0.12em;
    text-transform: uppercase; color: var(--amber); margin-bottom: 6px;
  }}
  h1 {{ font-size: 26px; font-weight: 700; margin: 0 0 4px; letter-spacing: -0.01em; }}
  .subtitle {{ color: var(--muted); font-size: 14px; }}

  .summary-strip {{
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 1px;
    background: var(--line); border: 1px solid var(--line); border-radius: 14px;
    overflow: hidden; margin: 18px 0;
  }}
  .summary-cell {{ background: var(--panel); padding: 14px 12px; }}
  .summary-cell .label {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; }}
  .summary-cell .val {{ font-family: 'IBM Plex Mono', monospace; font-size: 17px; margin-top: 4px; font-weight: 500; }}

  .swap-banner {{
    display: flex; gap: 12px; align-items: center; background: rgba(227,168,87,0.12);
    border: 1px solid rgba(227,168,87,0.35); border-radius: 14px; padding: 12px 14px; margin: 0 0 20px;
  }}
  .swap-icon {{ font-size: 20px; color: var(--amber); }}
  .swap-title {{ font-weight: 600; font-size: 14px; }}
  .swap-detail {{ font-size: 13px; color: var(--muted); margin-top: 2px; }}

  .rows {{ display: flex; flex-direction: column; gap: 10px; }}
  details.row {{
    background: var(--panel); border: 1px solid var(--line); border-left: 3px solid var(--line);
    border-radius: 12px; overflow: hidden;
  }}
  details.row[open] {{ border-left-width: 3px; }}
  details.row.gain {{ border-left-color: var(--gain); }}
  details.row.loss {{ border-left-color: var(--loss); }}
  details.row summary {{
    list-style: none; cursor: pointer; display: grid;
    grid-template-columns: 30px 1fr auto auto 18px; align-items: center; gap: 10px;
    padding: 12px 12px; -webkit-tap-highlight-color: transparent;
  }}
  details.row summary::-webkit-details-marker {{ display: none; }}
  details.row summary::marker {{ content: ""; }}
  .chevron {{ color: var(--muted); font-size: 18px; transition: transform 0.2s ease; justify-self: end; }}
  details.row[open] .chevron {{ transform: rotate(90deg); color: var(--amber); }}
  .rank {{ font-family: 'IBM Plex Mono', monospace; color: var(--muted); font-size: 13px; }}
  .name-line {{ display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }}
  .name {{ font-weight: 600; font-size: 14.5px; }}
  .horizon {{ font-size: 10.5px; color: var(--muted); border: 1px solid var(--line); border-radius: 20px; padding: 1px 8px; }}
  .tag-new {{ font-size: 10px; color: var(--ink); background: var(--amber); border-radius: 20px; padding: 1px 8px; font-weight: 600; }}
  .meta {{ font-size: 11.5px; color: var(--muted); margin-top: 4px; font-family: 'IBM Plex Mono', monospace; }}
  .spark-wrap {{ display: none; }}
  @media (min-width: 480px) {{ .spark-wrap {{ display: block; }} }}
  .numbers {{ text-align: right; }}
  .value {{ font-family: 'IBM Plex Mono', monospace; font-size: 14.5px; font-weight: 500; }}
  .return {{ font-family: 'IBM Plex Mono', monospace; font-size: 12.5px; margin-top: 2px; }}
  details.row.gain .return {{ color: var(--gain); }}
  details.row.loss .return {{ color: var(--loss); }}

  .detail-panel {{
    border-top: 1px solid var(--line); background: var(--panel-2);
    padding: 14px 14px 16px; animation: fade-in 0.15s ease;
  }}
  @keyframes fade-in {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
  .detail-panel h3 {{
    font-size: 11px; text-transform: uppercase; letter-spacing: 0.07em; color: var(--muted);
    margin: 12px 0 8px; font-weight: 600;
  }}
  .detail-panel h3:first-child {{ margin-top: 0; }}
  table.pos-table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
  table.pos-table th {{ text-align: left; color: var(--muted); font-weight: 500; padding: 4px 6px; border-bottom: 1px solid var(--line); font-family: 'IBM Plex Mono', monospace; }}
  table.pos-table td {{ padding: 7px 6px; border-bottom: 1px solid var(--line); font-family: 'IBM Plex Mono', monospace; }}
  table.pos-table tr:last-child td {{ border-bottom: none; }}
  .asset-name {{ font-family: 'IBM Plex Sans', sans-serif; font-size: 12.5px; color: var(--text); white-space: normal; }}
  .asset-ticker {{ color: var(--muted); font-size: 10.5px; margin-top: 1px; }}
  ul.trade-log {{ list-style: none; margin: 0; padding: 0; font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: var(--muted); }}
  ul.trade-log li {{ padding: 5px 0; border-bottom: 1px solid var(--line); }}
  ul.trade-log li:last-child {{ border-bottom: none; }}
  .empty-note {{ font-size: 12.5px; color: var(--muted); font-style: italic; }}

  .log-section {{ margin-top: 28px; }}
  .log-section h2 {{
    font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted);
    margin: 0 0 10px; font-weight: 600;
  }}
  ul.swap-log {{ list-style: none; margin: 0; padding: 0; font-family: 'IBM Plex Mono', monospace; font-size: 12.5px; }}
  ul.swap-log li {{ padding: 7px 2px; border-bottom: 1px solid var(--line); color: var(--muted); }}
  .log-week {{ color: var(--amber); margin-right: 8px; }}
  .log-removed {{ color: var(--loss); }}
  .log-added {{ color: var(--gain); }}

  footer {{ margin-top: 28px; font-size: 11px; color: var(--muted); text-align: center; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="eyebrow">Bot A · Kontrollzentrum</div>
    <h1>Strategie-Ranking</h1>
    <div class="subtitle">Woche {week} · Stand {datetime.now():%d.%m.%Y, %H:%M} Uhr · Zeile antippen für Details</div>
  </header>

  <div class="summary-strip">
    <div class="summary-cell"><div class="label">Gesamtwert</div><div class="val">{total_value:,.0f} €</div></div>
    <div class="summary-cell"><div class="label">Beste</div><div class="val" style="color:var(--gain)">{best['total_return_pct']:+.2f}%</div></div>
    <div class="summary-cell"><div class="label">Gebühren ges.</div><div class="val">{total_fees:.2f} €</div></div>
  </div>

  {swap_banner}

  <div class="rows">
    {''.join(rows_html)}
  </div>

  <div class="log-section">
    <h2>Tausch-Verlauf</h2>
    <ul class="swap-log">
      {swap_log_html if swap_log_html else '<li>Noch keine Tauschvorgänge</li>'}
    </ul>
  </div>

  <footer>Paper-Trading-Simulation · Gebühren nach Scalable-Capital-Preisverzeichnis · Keine Anlageberatung</footer>
</div>
</body>
</html>"""

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path
