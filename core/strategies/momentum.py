"""
Estrategia de Momentum.
Compra cuando el precio muestra tendencia alcista sostenida.
Vende cuando la tendencia se revierte.
"""

from typing import Optional
from .base import BaseStrategy, Signal


class MomentumStrategy(BaseStrategy):
    """
    Detecta momentum en precios de mercados de predicción.

    Lógica:
    - Si el precio de YES sube consistentemente → comprar YES
    - Si el precio de YES baja consistentemente → comprar NO
    - Usa lookback period y threshold configurables
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.lookback = config.get("lookback_period", 24)
        self.threshold = config.get("threshold", 0.05)

    def analyze(self, market: dict, price_history: list[dict],
                market_data_service=None) -> Optional[Signal]:
        """Analiza momentum del mercado."""

        if len(price_history) < self.lookback:
            return None

        recent = price_history[-self.lookback:]
        prices = [p["price"] for p in recent]

        if not prices or prices[0] == 0:
            return None

        # Calcular cambio porcentual
        price_change = (prices[-1] - prices[0]) / prices[0]

        # Calcular consistencia de la tendencia
        up_moves = sum(
            1 for i in range(1, len(prices)) if prices[i] > prices[i - 1]
        )
        consistency = up_moves / (len(prices) - 1) if len(prices) > 1 else 0

        current_price = prices[-1]

        # Señal de compra YES: precio subiendo con consistencia
        if (
            price_change > self.threshold
            and consistency > 0.6
            and current_price < 0.85
        ):
            confidence = min(
                abs(price_change) * consistency * 2, 0.95
            )
            return Signal(
                action="buy",
                market=market,
                outcome="yes",
                confidence=confidence,
                reason=(
                    f"Momentum alcista: {price_change:+.2%} "
                    f"en {self.lookback} períodos "
                    f"(consistencia: {consistency:.0%})"
                ),
                amount_pct=self.get_position_size(confidence),
            )

        # Señal de compra NO: precio bajando con consistencia
        if (
            price_change < -self.threshold
            and consistency < 0.4
            and current_price > 0.15
        ):
            confidence = min(
                abs(price_change) * (1 - consistency) * 2, 0.95
            )
            return Signal(
                action="buy",
                market=market,
                outcome="no",
                confidence=confidence,
                reason=(
                    f"Momentum bajista: {price_change:+.2%} "
                    f"en {self.lookback} períodos "
                    f"(consistencia bajista: {1 - consistency:.0%})"
                ),
                amount_pct=self.get_position_size(confidence),
            )

        return None

    def should_close(self, trade: dict, current_price: float,
                     price_history: list[dict]) -> bool:
        """Cierra si el momentum se revierte."""
        if len(price_history) < 5:
            return False

        recent = [p["price"] for p in price_history[-5:]]
        entry = trade["entry_price"]
        outcome = trade.get("outcome", "yes")

        if outcome == "yes":
            # Cerrar YES si precio cae significativamente
            short_change = (recent[-1] - recent[0]) / recent[0] if recent[0] > 0 else 0
            if short_change < -self.threshold * 0.5:
                self._log(
                    f"Momentum revertido para YES: {short_change:+.2%}"
                )
                return True
        else:
            # Cerrar NO si precio sube significativamente
            short_change = (recent[-1] - recent[0]) / recent[0] if recent[0] > 0 else 0
            if short_change > self.threshold * 0.5:
                self._log(
                    f"Momentum revertido para NO: {short_change:+.2%}"
                )
                return True

        return False
