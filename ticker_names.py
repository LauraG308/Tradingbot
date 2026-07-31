"""
Vollständige Bezeichnungen der verwendeten Ticker (für Anzeige im Dashboard).
Bei Erweiterung des Ticker-Universums hier ergänzen.
"""

TICKER_NAMES = {
    "URTH": "iShares MSCI World ETF",
    "VT": "Vanguard Total World Stock ETF",
    "VYM": "Vanguard High Dividend Yield ETF",
    "SCHD": "Schwab US Dividend Equity ETF",
    "SPY": "SPDR S&P 500 ETF Trust",
    "QQQ": "Invesco QQQ Trust (Nasdaq-100)",
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
    "MTUM": "iShares MSCI USA Momentum Factor ETF",
    "QUAL": "iShares MSCI USA Quality Factor ETF",
    "SMH": "VanEck Semiconductor ETF",
    "RSP": "Invesco S&P 500 Equal Weight ETF",
    "USMV": "iShares MSCI USA Min Vol Factor ETF",
    "SPLV": "Invesco S&P 500 Low Volatility ETF",
    "SOXX": "iShares Semiconductor ETF",
}


def full_name(ticker: str) -> str:
    return TICKER_NAMES.get(ticker, ticker)
