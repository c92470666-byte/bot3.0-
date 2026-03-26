"""
Estrategia de Arbitraje.
Busca ineficiencias de precio entre YES y NO del mismo mercado.
"""

from typing import Optional
from .base import BaseStrategy, Signal


class ArbitrageStrategy(BaseStrategy):
    """
    Detecta oportunidades de arbitraje cuando:
    - YES + NO < 1.0 (comprar ambos = ganancia garantizada)
    - YES + NO > 1.0 (vender ambos = ganancia garantizada)
    - Spread excesivo entre bid/ask
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.min_spread = config.get("min_spread", 0.02)

    def analyze(self, market: dict, price_history: list[dict],
                market_data_service=None) -> Optional[Signal]:
        """Busca oportunidades de arbitraje."""

        yes_price = market.get("yes_price", 0.5)
        no_price = market.get("no_price", 0.5)

        total = yes_price + no_price

        # Arbitraje: YES + NO < 1 (comprar ambos)
        if total < (1.0 - self.min_spread):
            gap = 1.0 - total
            confidence = min(gap * 10, 0.95)

            # Comprar el más barato
            if yes_price <= no_price:
                outcome = "yes"
                price = yes_price
            else:
                outcome = "no"
                price = no_price

            return Signal(
                action="buy",
                market=market,
                outcome=outcome,
                confidence=confidence,
                reason=(
                    f"Arbitraje: YES({yes_price:.3f}) + "
                    f"NO({no_price:.3f}) = {total:.3f} < 1.0 "
                    f"(gap: {gap:.3f})"
                ),
                amount_pct=self.get_position_size(confidence, base_pct=8.0),
            )

        # Precio extremo con alta confianza
        if yes_price < 0.10 and no_price > 0.85:
            # YES muy barato, posible valor
            return Signal(
                action="buy",
                market=market,
                outcome="yes",
                confidence=0.3,
                reason=(
                    f"YES extremadamente barato ({yes_price:.3f}), "
                    f"posible valor residual"
                ),
                amount_pct=2.0,
            )

        if no_price < 0.10 and yes_price > 0.85:
            return Signal(
                action="buy",
                market=market,
                outcome="no",
                confidence=0.3,
                reason=(
                    f"NO extremadamente barato ({no_price:.3f}), "
                    f"posible valor residual"
                ),
                amount_pct=2.0,
            )

        return None

    def should_close(self, trade: dict, current_price: float,
                     price_history: list[dict]) -> bool:
        """Cierra cuando el gap de arbitraje se cierra."""
        entry = trade.get("entry_price", 0)

        if entry == 0:
            return False

        # Si ganamos más del 50% del gap, cerrar
        pnl_pct = ((current_price - entry) / entry) * 100 if entry > 0 else 0

        if pnl_pct > 3.0:
            self._log(f"Gap de arbitraje cerrado, P&L: {pnl_pct:+.2f}%")
            return True

        return False
