"""
Estrategia basada en Sentimiento / Volumen.
Analiza volumen y acción del precio para detectar interés del mercado.
"""

from typing import Optional
import numpy as np
from .base import BaseStrategy, Signal


class SentimentStrategy(BaseStrategy):
    """
    Detecta cambios de sentimiento basándose en:
    - Volumen inusual
    - Velocidad de cambio de precio
    - Divergencias precio/volumen
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.sources = config.get("sources", ["volume", "price_action"])
        self.volume_threshold = config.get("volume_threshold", 2.0)
        self.price_velocity_threshold = config.get(
            "price_velocity_threshold", 0.03
        )

    def analyze(self, market: dict, price_history: list[dict],
                market_data_service=None) -> Optional[Signal]:
        """Analiza sentimiento del mercado."""

        signals_collected = []

        # Análisis de volumen
        if "volume" in self.sources:
            vol_signal = self._analyze_volume(market)
            if vol_signal:
                signals_collected.append(vol_signal)

        # Análisis de acción del precio
        if "price_action" in self.sources and len(price_history) >= 10:
            pa_signal = self._analyze_price_action(market, price_history)
            if pa_signal:
                signals_collected.append(pa_signal)

        if not signals_collected:
            return None

        # Combinar señales
        return self._combine_signals(signals_collected, market)

    def _analyze_volume(self, market: dict) -> Optional[dict]:
        """Analiza si el volumen es inusualmente alto."""
        volume = market.get("volume", 0)
        liquidity = market.get("liquidity", 0)

        if liquidity == 0:
            return None

        # Ratio volumen/liquidez como proxy de actividad
        vol_ratio = volume / liquidity

        if vol_ratio > self.volume_threshold:
            yes_price = market.get("yes_price", 0.5)

            # Alto volumen + precio bajo = posible oportunidad YES
            if yes_price < 0.4:
                return {
                    "direction": "yes",
                    "confidence": min(vol_ratio / 10, 0.7),
                    "reason": (
                        f"Volumen alto ({vol_ratio:.1f}x liquidez) "
                        f"con YES barato ({yes_price:.2f})"
                    ),
                }
            # Alto volumen + precio alto = confirma tendencia
            elif yes_price > 0.7:
                return {
                    "direction": "yes",
                    "confidence": min(vol_ratio / 15, 0.6),
                    "reason": (
                        f"Volumen alto ({vol_ratio:.1f}x) "
                        f"confirma tendencia YES ({yes_price:.2f})"
                    ),
                }

        return None

    def _analyze_price_action(self, market: dict,
                              price_history: list[dict]) -> Optional[dict]:
        """Analiza la velocidad y dirección del cambio de precio."""
        if len(price_history) < 10:
            return None

        prices = [p["price"] for p in price_history[-10:]]

        # Calcular velocidad de cambio (derivada)
        velocities = []
        for i in range(1, len(prices)):
            if prices[i - 1] > 0:
                vel = (prices[i] - prices[i - 1]) / prices[i - 1]
                velocities.append(vel)

        if not velocities:
            return None

        avg_velocity = np.mean(velocities)
        recent_velocity = np.mean(velocities[-3:]) if len(velocities) >= 3 else avg_velocity

        # Aceleración positiva fuerte
        if recent_velocity > self.price_velocity_threshold:
            current = prices[-1]
            if current < 0.85:
                return {
                    "direction": "yes",
                    "confidence": min(abs(recent_velocity) * 5, 0.75),
                    "reason": (
                        f"Aceleración de precio positiva: "
                        f"{recent_velocity:+.3f}/período"
                    ),
                }

        # Aceleración negativa fuerte
        elif recent_velocity < -self.price_velocity_threshold:
            current = prices[-1]
            if current > 0.15:
                return {
                    "direction": "no",
                    "confidence": min(abs(recent_velocity) * 5, 0.75),
                    "reason": (
                        f"Aceleración de precio negativa: "
                        f"{recent_velocity:+.3f}/período"
                    ),
                }

        return None

    def _combine_signals(self, signals: list[dict],
                         market: dict) -> Optional[Signal]:
        """Combina múltiples sub-señales en una señal final."""
        if not signals:
            return None

        # Contar direcciones
        yes_signals = [s for s in signals if s["direction"] == "yes"]
        no_signals = [s for s in signals if s["direction"] == "no"]

        if len(yes_signals) >= len(no_signals) and yes_signals:
            avg_conf = np.mean([s["confidence"] for s in yes_signals])
            reasons = " + ".join([s["reason"] for s in yes_signals])
            return Signal(
                action="buy",
                market=market,
                outcome="yes",
                confidence=min(avg_conf * 1.1, 0.90),
                reason=f"Sentimiento positivo: {reasons}",
                amount_pct=self.get_position_size(avg_conf),
            )
        elif no_signals:
            avg_conf = np.mean([s["confidence"] for s in no_signals])
            reasons = " + ".join([s["reason"] for s in no_signals])
            return Signal(
                action="buy",
                market=market,
                outcome="no",
                confidence=min(avg_conf * 1.1, 0.90),
                reason=f"Sentimiento negativo: {reasons}",
                amount_pct=self.get_position_size(avg_conf),
            )

        return None

    def should_close(self, trade: dict, current_price: float,
                     price_history: list[dict]) -> bool:
        """Cierra si el sentimiento se revierte."""
        if len(price_history) < 5:
            return False

        prices = [p["price"] for p in price_history[-5:]]
        velocities = []
        for i in range(1, len(prices)):
            if prices[i - 1] > 0:
                vel = (prices[i] - prices[i - 1]) / prices[i - 1]
                velocities.append(vel)

        if not velocities:
            return False

        avg_vel = np.mean(velocities)
        outcome = trade.get("outcome", "yes")

        # Si compramos YES y velocidad se vuelve negativa
        if outcome == "yes" and avg_vel < -self.price_velocity_threshold:
            self._log("Sentimiento revertido contra posición YES")
            return True

        # Si compramos NO y velocidad se vuelve positiva
        if outcome == "no" and avg_vel > self.price_velocity_threshold:
            self._log("Sentimiento revertido contra posición NO")
            return True

        return False
