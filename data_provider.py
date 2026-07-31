"""
Kursdaten-Beschaffung. Nutzt yfinance (kostenlos, ausreichend für Paper Trading).
Für produktiven/hochfrequenten Einsatz ggf. durch einen bezahlten Datenfeed ersetzen.

Installation auf deinem Rechner:
    pip install yfinance pandas
"""

import yfinance as yf
import pandas as pd


def get_price_history(tickers: list[str], period: str = "1y",
                       interval: str = "1d") -> dict[str, pd.DataFrame]:
    result = {}
    for ticker in tickers:
        try:
            df = yf.Ticker(ticker).history(period=period, interval=interval)
            result[ticker] = df
        except Exception as e:
            print(f"[WARN] Konnte Kursdaten für {ticker} nicht laden: {e}")
            result[ticker] = pd.DataFrame()
    return result


def get_latest_prices(tickers: list[str]) -> dict[str, float]:
    prices = {}
    for ticker in tickers:
        try:
            df = yf.Ticker(ticker).history(period="5d")
            prices[ticker] = float(df["Close"].iloc[-1])
        except Exception:
            prices[ticker] = None
    return prices
