"""
Ein StrategyBot simuliert genau eine Strategie (Paper Trading) auf einem
Ticker-Universum, inkl. Scalable-Capital-Gebühren.
"""

from dataclasses import dataclass, field
import pandas as pd
from fees import ScalableCapitalFees
from ticker_names import full_name


@dataclass
class Position:
    ticker: str
    shares: float = 0.0
    avg_price: float = 0.0


class StrategyBot:
    def __init__(self, strategy: dict, starting_capital: float,
                 fee_model: ScalableCapitalFees):
        self.strategy = strategy
        self.cash = starting_capital
        self.starting_capital = starting_capital
        self.fee_model = fee_model
        self.positions: dict[str, Position] = {
            t: Position(t) for t in strategy["tickers"]
        }
        self.total_fees_paid = 0.0
        self.trade_log = []

    @property
    def name(self):
        return self.strategy["name"]

    def _portfolio_value(self, prices: dict[str, float]) -> float:
        value = self.cash
        for t, pos in self.positions.items():
            value += pos.shares * prices.get(t, pos.avg_price)
        return value

    def _n_tickers(self):
        return len(self.strategy["tickers"])

    def process_week(self, price_history: dict[str, pd.DataFrame]):
        """price_history: {ticker: DataFrame mit Spalte 'Close', neueste Zeile = aktuell}"""
        signal_fn = self.strategy["signal_fn"]
        is_savings_plan = self.strategy["is_savings_plan"]

        for ticker, df in price_history.items():
            if df.empty:
                continue
            signal = signal_fn(df)
            price = float(df["Close"].iloc[-1])
            pos = self.positions[ticker]

            if signal == "buy":
                budget = self.cash / max(self._n_tickers(), 1)
                if budget <= 1:
                    continue
                shares_to_buy = budget / price
                cost = shares_to_buy * price
                fee = self.fee_model.order_cost(cost, is_savings_plan).total
                if cost + fee > self.cash:
                    continue
                self.cash -= (cost + fee)
                self.total_fees_paid += fee
                new_total_shares = pos.shares + shares_to_buy
                pos.avg_price = (
                    (pos.avg_price * pos.shares + price * shares_to_buy) / new_total_shares
                    if new_total_shares > 0 else price
                )
                pos.shares = new_total_shares
                self.trade_log.append(
                    f"BUY {full_name(ticker)} ({ticker}): {shares_to_buy:.4f} @ {price:.2f} (Gebühr {fee:.2f} €)"
                )

            elif signal == "sell" and pos.shares > 0:
                proceeds = pos.shares * price
                fee = self.fee_model.order_cost(proceeds, is_savings_plan).total
                self.cash += (proceeds - fee)
                self.total_fees_paid += fee
                self.trade_log.append(
                    f"SELL {full_name(ticker)} ({ticker}): {pos.shares:.4f} @ {price:.2f} (Gebühr {fee:.2f} €)"
                )
                pos.shares = 0.0
                pos.avg_price = 0.0

    def performance_report(self, current_prices: dict[str, float]) -> dict:
        value = self._portfolio_value(current_prices)
        total_return_pct = (value - self.starting_capital) / self.starting_capital * 100
        return {
            "strategy_id": self.strategy["id"],
            "name": self.name,
            "horizon": self.strategy["horizon"],
            "value": round(value, 2),
            "total_return_pct": round(total_return_pct, 2),
            "fees_paid": round(self.total_fees_paid, 2),
            "cash": round(self.cash, 2),
        }
