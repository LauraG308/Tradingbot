"""
Bot A – Orchestrator.

Aufgaben:
  1. Lädt/verwaltet den Zustand der 5 Strategie-Bots (persistiert in state.json).
  2. Führt für jeden Bot wöchentlich process_week() aus (Signale + Trades inkl. Gebühren).
  3. Erstellt einen Wochenbericht (Ranking nach Performance nach Gebühren).
  4. Ersetzt die schlechteste Strategie durch eine neue aus dem Strategie-Pool.

Ausführung: 1x pro Woche via Cron/Taskplaner (siehe README.md).
"""

import json
import os
from datetime import datetime

from config import STARTING_CAPITAL_PER_BOT, FEE_TARIFF, FEE_VENUE, STATE_FILE, LOG_FILE
from fees import ScalableCapitalFees
from strategy_bot import StrategyBot
from strategy_library import STRATEGY_POOL, get_starting_five, get_replacement
import data_provider
from dashboard_generator import render_dashboard

HISTORY_FILE = "history.json"


def load_history() -> dict:
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_history(history: dict):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def _find_strategy(strategy_id: str) -> dict:
    for s in STRATEGY_POOL:
        if s["id"] == strategy_id:
            return s
    raise KeyError(strategy_id)


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    # Erststart: 5 Startstrategien mit vollem Kapital
    return {
        "bots": [
            {
                "strategy_id": s["id"],
                "cash": STARTING_CAPITAL_PER_BOT,
                "positions": {t: {"shares": 0.0, "avg_price": 0.0} for t in s["tickers"]},
                "total_fees_paid": 0.0,
                "starting_capital": STARTING_CAPITAL_PER_BOT,
            }
            for s in get_starting_five()
        ],
        "week": 0,
        "swap_history": [],
    }


def save_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def _rebuild_bot(bot_state: dict, fee_model: ScalableCapitalFees) -> StrategyBot:
    strategy = _find_strategy(bot_state["strategy_id"])
    bot = StrategyBot(strategy, bot_state["starting_capital"], fee_model)
    bot.cash = bot_state["cash"]
    bot.total_fees_paid = bot_state["total_fees_paid"]
    for t, p in bot_state["positions"].items():
        if t in bot.positions:
            bot.positions[t].shares = p["shares"]
            bot.positions[t].avg_price = p["avg_price"]
    return bot


def _bot_to_state(bot: StrategyBot) -> dict:
    return {
        "strategy_id": bot.strategy["id"],
        "cash": bot.cash,
        "positions": {t: {"shares": p.shares, "avg_price": p.avg_price}
                      for t, p in bot.positions.items()},
        "total_fees_paid": bot.total_fees_paid,
        "starting_capital": bot.starting_capital,
    }


def run_weekly_cycle():
    state = load_state()
    fee_model = ScalableCapitalFees(tariff=FEE_TARIFF, venue=FEE_VENUE)

    bots = [_rebuild_bot(bs, fee_model) for bs in state["bots"]]

    reports = []
    details = {}
    for bot in bots:
        price_history = data_provider.get_price_history(bot.strategy["tickers"])
        bot.process_week(price_history)
        latest_prices = {t: float(df["Close"].iloc[-1]) if not df.empty else None
                          for t, df in price_history.items()}
        reports.append(bot.performance_report(latest_prices))

        positions_detail = []
        for ticker, pos in bot.positions.items():
            current_price = latest_prices.get(ticker) or pos.avg_price
            positions_detail.append({
                "ticker": ticker,
                "shares": pos.shares,
                "avg_price": pos.avg_price,
                "current_price": current_price,
                "market_value": pos.shares * current_price,
            })
        details[bot.strategy["id"]] = {
            "positions": positions_detail,
            "trade_log": list(bot.trade_log),
        }

    reports_sorted = sorted(reports, key=lambda r: r["total_return_pct"], reverse=True)

    # Verlaufswerte je Strategie fortschreiben (für Sparklines im Dashboard)
    history = load_history()
    for r in reports:
        history.setdefault(r["strategy_id"], []).append(r["value"])
        history[r["strategy_id"]] = history[r["strategy_id"]][-26:]  # max ~ein halbes Jahr

    lines = [f"\n=== Bot A Wochenbericht – {datetime.now():%Y-%m-%d %H:%M} (Woche {state['week']+1}) ==="]
    for rank, r in enumerate(reports_sorted, 1):
        lines.append(
            f"{rank}. {r['name']} [{r['horizon']}] – "
            f"Wert: {r['value']:.2f} € | Rendite: {r['total_return_pct']:.2f}% | "
            f"Gebühren gesamt: {r['fees_paid']:.2f} €"
        )

    worst = reports_sorted[-1]
    active_ids = {r["strategy_id"] for r in reports}
    new_strategy = get_replacement(active_ids)

    lines.append(
        f"\n>> Schlechteste Strategie: '{worst['name']}' (Rendite {worst['total_return_pct']:.2f}%) "
        f"wird ersetzt durch: '{new_strategy['name']}'"
    )

    # Zustand aktualisieren: schlechtesten Bot durch neue Strategie ersetzen,
    # verbleibendes Kapital (nach Gebühren) wird zum neuen Startkapital
    new_bots_state = []
    for bot in bots:
        if bot.strategy["id"] == worst["strategy_id"]:
            remaining_value = worst["value"]
            new_bots_state.append({
                "strategy_id": new_strategy["id"],
                "cash": remaining_value,
                "positions": {t: {"shares": 0.0, "avg_price": 0.0} for t in new_strategy["tickers"]},
                "total_fees_paid": 0.0,
                "starting_capital": remaining_value,
            })
        else:
            new_bots_state.append(_bot_to_state(bot))

    state["bots"] = new_bots_state
    state["week"] += 1
    state["swap_history"].append({
        "week": state["week"],
        "removed": worst["strategy_id"],
        "added": new_strategy["id"],
        "date": datetime.now().isoformat(),
    })

    save_state(state)
    save_history(history)

    # Für neu eingesetzte Strategie noch keinen Verlauf -> Startwert einmalig eintragen
    history.setdefault(new_strategy["id"], [])
    if not history[new_strategy["id"]]:
        history[new_strategy["id"]].append(worst["value"])
        save_history(history)

    dashboard_path = render_dashboard(
        reports_sorted=reports_sorted,
        history=history,
        swap_history=state["swap_history"],
        week=state["week"],
        details=details,
    )

    report_text = "\n".join(lines)
    print(report_text)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(report_text + "\n")
    print(f"Dashboard aktualisiert: {dashboard_path}")

    return report_text


if __name__ == "__main__":
    run_weekly_cycle()
