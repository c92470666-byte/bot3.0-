"""
Estrategia de Reversión a la Media.
Compra cuando el precio se desvía significativamente de su media.
"""

from typing import Optional
import numpy as np
from .base import BaseStrategy, Signal


class MeanReversionStrategy(BaseStrategy):
    """
    Apuesta a que precios extremos revertirán a la media.

    Lógica:
    - Si YES está muy barato vs su media → comprar YES
    - Si YES está muy caro vs su media → comprar NO
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.lookback = config.get("lookback_period", 48)
        self.std_multiplier = config.get("std_multiplier", 2.0)

    def analyze(self, market: dict, price_history: list[dict],
                market_data_service=None) -> Optional[Signal]:
        """Analiza desviación de la media."""

        if len(price_history) < self.lookback:
            return None

        recent = price_history[-self.lookback:]
        prices = np.array([p["price"] for p in recent])

        mean_price = np.mean(prices)
        std_price = np.std(prices)

        if std_price == 0:
            return None

        current_price = prices[-1]
        z_score = (current_price - mean_price) / std_price

        # Precio muy por debajo de la media → comprar YES
        if z_score < -self.std_multiplier and current_price < 0.80:
            confidence = min(abs(z_score) / 4, 0.90)
            return Signal(
                action="buy",
                market=market,
                outcome="yes",
                confidence=confidence,
                reason=(
                    f"Precio bajo vs media: z-score={z_score:.2f} "
                    f"(precio={current_price:.3f}, "
                    f"media={mean_price:.3f})"
                ),
                amount_pct=self.get_position_size(confidence),
            )

        # Precio muy por encima de la media → comprar NO
        if z_score > self.std_multiplier and current_price > 0.20:
            confidence = min(abs(z_score) / 4, 0.90)
            return Signal(
                action="buy",
                market=market,
                outcome="no",
                confidence=confidence,
                reason=(
                    f"Precio alto vs media: z-score={z_score:.2f} "
                    f"(precio={current_price:.3f}, "
                    f"media={mean_price:.3f})"
                ),
                amount_pct=self.get_position_size(confidence),
            )

        return None

    def should_close(self, trade: dict, current_price: float,
                     price_history: list[dict]) -> bool:
        """Cierra cuando el precio vuelve a la media."""
        if len(price_history) < 10:
            return False

        prices = np.array([p["price"] for p in price_history[-self.lookback:]])
        mean_price = np.mean(prices)
        std_price = np.std(prices)

        if std_price == 0:
            return False

        z_score = (current_price - mean_price) / std_price

        # Cerrar cuando vuelve cerca de la media
        if abs(z_score) < 0.5:
            self._log(
                f"Precio volvió a la media: z={z_score:.2f}"
            )
            return True

        return False
