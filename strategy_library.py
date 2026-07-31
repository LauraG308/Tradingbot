"""
Pool aktuell gefragter Anlagestrategien (Stand Juli 2026), aus denen Bot A
bei Bedarf eine neue, noch nicht aktive Strategie zieht.

Jede Strategie ist ein Dict mit:
  - name: Anzeigename
  - horizon: "long" | "medium" | "short"
  - tickers: Kürzel-Universum (ETFs/Aktien)
  - is_savings_plan: ob per ETF-Sparplan (gebührenfrei) ausgeführt wird
  - signal_fn: Funktion(df) -> "buy" | "sell" | "hold" pro Zeitreihe

Die Signalfunktionen sind bewusst einfach gehalten (Referenzimplementierung).
Für produktiven Einsatz würde man sie verfeinern/backtesten.
"""

import pandas as pd


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss.replace(0, 1e-9)
    return 100 - (100 / (1 + rs))


def signal_buy_and_hold(df: pd.DataFrame) -> str:
    # Kauft einmalig/regelmäßig, hält danach durch (ETF-Sparplan-Logik)
    return "buy"


def signal_golden_cross(df: pd.DataFrame) -> str:
    ma50 = df["Close"].rolling(50).mean()
    ma200 = df["Close"].rolling(200).mean()
    if len(ma50) < 200 or ma50.iloc[-1] is None:
        return "hold"
    if ma50.iloc[-1] > ma200.iloc[-1] and ma50.iloc[-2] <= ma200.iloc[-2]:
        return "buy"
    if ma50.iloc[-1] < ma200.iloc[-1] and ma50.iloc[-2] >= ma200.iloc[-2]:
        return "sell"
    return "hold"


def signal_rsi_swing(df: pd.DataFrame) -> str:
    rsi = _rsi(df["Close"])
    if rsi.empty or pd.isna(rsi.iloc[-1]):
        return "hold"
    if rsi.iloc[-1] < 30:
        return "buy"
    if rsi.iloc[-1] > 70:
        return "sell"
    return "hold"


def signal_dividend_value(df: pd.DataFrame) -> str:
    # Vereinfachtes Proxy-Signal: Kurs deutlich unter 200-Tage-Linie = "günstig"
    ma200 = df["Close"].rolling(200).mean()
    if len(ma200) < 200:
        return "hold"
    if df["Close"].iloc[-1] < 0.95 * ma200.iloc[-1]:
        return "buy"
    return "hold"


def signal_relative_strength(df: pd.DataFrame) -> str:
    ret_4w = df["Close"].pct_change(20)
    if ret_4w.empty or pd.isna(ret_4w.iloc[-1]):
        return "hold"
    if ret_4w.iloc[-1] > 0.05:
        return "buy"
    if ret_4w.iloc[-1] < -0.05:
        return "sell"
    return "hold"


# Pool: aktive 5 Startstrategien + weitere Kandidaten zur Rotation
STRATEGY_POOL = [
    {
        "id": "buyhold_world_etf",
        "name": "Langfristiger ETF-Sparplan (MSCI World / All-World)",
        "horizon": "long",
        "tickers": ["URTH", "VT"],
        "is_savings_plan": True,
        "signal_fn": signal_buy_and_hold,
    },
    {
        "id": "dividend_value",
        "name": "Dividenden-/Value-Strategie (Aristocrats-Proxy)",
        "horizon": "long",
        "tickers": ["VYM", "SCHD"],
        "is_savings_plan": False,
        "signal_fn": signal_dividend_value,
    },
    {
        "id": "golden_cross_trend",
        "name": "Trendfolge (Golden Cross 50/200)",
        "horizon": "medium",
        "tickers": ["SPY", "QQQ"],
        "is_savings_plan": False,
        "signal_fn": signal_golden_cross,
    },
    {
        "id": "rsi_swing",
        "name": "Kurzfristiges Swing-Trading (RSI Mean-Reversion)",
        "horizon": "short",
        "tickers": ["AAPL", "MSFT", "NVDA"],
        "is_savings_plan": False,
        "signal_fn": signal_rsi_swing,
    },
    {
        "id": "core_satellite_factor",
        "name": "Core-Satellite mit Faktor-/Themen-ETFs",
        "horizon": "medium",
        "tickers": ["MTUM", "QUAL", "SMH"],
        "is_savings_plan": False,
        "signal_fn": signal_relative_strength,
    },
    # --- Rotations-Kandidaten (werden bei Ablösung gezogen) ---
    {
        "id": "equal_weight_sp500",
        "name": "Equal-Weight S&P 500",
        "horizon": "long",
        "tickers": ["RSP"],
        "is_savings_plan": True,
        "signal_fn": signal_buy_and_hold,
    },
    {
        "id": "low_volatility_factor",
        "name": "Low-Volatility-Faktor",
        "horizon": "medium",
        "tickers": ["USMV", "SPLV"],
        "is_savings_plan": False,
        "signal_fn": signal_relative_strength,
    },
    {
        "id": "ai_tech_momentum",
        "name": "KI-/Tech-Growth-Momentum",
        "horizon": "short",
        "tickers": ["SMH", "SOXX", "NVDA"],
        "is_savings_plan": False,
        "signal_fn": signal_rsi_swing,
    },
]


def get_starting_five():
    return STRATEGY_POOL[:5]


def get_replacement(active_ids: set):
    """Liefert die nächste noch nicht aktive Strategie aus dem Pool."""
    for strat in STRATEGY_POOL:
        if strat["id"] not in active_ids:
            return strat
    raise RuntimeError("Kein Ersatzkandidat mehr im Pool – STRATEGY_POOL erweitern.")
