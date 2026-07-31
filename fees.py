"""
Gebührenmodell Scalable Capital – Stand: Juli 2026 (FREE Broker Tarif).
Quelle: Scalable Capital Preisverzeichnis / Marktvergleiche (Juli 2026).

Passe TARIFF an, falls du PRIME+ nutzt oder sich die Konditionen ändern
(Stichprobe regelmäßig gegen die offizielle Preisliste prüfen!).
"""

from dataclasses import dataclass


@dataclass
class FeeResult:
    order_fee: float          # feste Ordergebühr
    venue_fee: float          # Handelsplatzgebühr (nur Xetra)
    total: float


class ScalableCapitalFees:
    """
    FREE Broker (Default):
      - gettex / EIX: 0,99 € pauschal pro Order, keine weiteren Kosten
      - Xetra: 3,99 € Ordergebühr + 0,01 % Handelsplatzgebühr (min. 1,50 €)
      - ETF-Sparplan (egal welcher Handelsplatz): 0,00 € Ausführungsgebühr

    PRIME+ (4,99 €/Monat, hier als Fixkosten separat verrechnet):
      - Einzelorder ab 250 € Volumen auf gettex/EIX: 0,00 €
      - unter 250 € Volumen: weiterhin 0,99 €
    """

    PRIME_PLUS_MONTHLY_FEE = 4.99

    def __init__(self, tariff: str = "FREE", venue: str = "gettex"):
        assert tariff in ("FREE", "PRIME_PLUS")
        assert venue in ("gettex", "xetra")
        self.tariff = tariff
        self.venue = venue

    def order_cost(self, volume_eur: float, is_savings_plan: bool = False) -> FeeResult:
        if is_savings_plan:
            # ETF-Sparplanausführung ist bei Scalable Capital immer kostenfrei
            return FeeResult(0.0, 0.0, 0.0)

        if self.venue == "xetra":
            order_fee = 3.99
            venue_fee = max(volume_eur * 0.0001, 1.50)  # 0,01 %, min. 1,50 €
            return FeeResult(order_fee, venue_fee, order_fee + venue_fee)

        # gettex / EIX
        if self.tariff == "PRIME_PLUS" and volume_eur >= 250:
            return FeeResult(0.0, 0.0, 0.0)
        return FeeResult(0.99, 0.0, 0.99)

    def monthly_fixed_cost(self) -> float:
        return self.PRIME_PLUS_MONTHLY_FEE if self.tariff == "PRIME_PLUS" else 0.0
