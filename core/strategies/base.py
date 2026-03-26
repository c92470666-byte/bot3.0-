"""
Estrategia base abstracta.
Todas las estrategias heredan de aquí.
"""

from abc import ABC, abstractmethod
from typing import Optional
from loguru import logger


class Signal:
    """Representa una señal de trading."""

    def __init__(self, action: str, market: dict, outcome: str,
                 confidence: float, reason: str, amount_pct: float = 5.0):
        self.action = action          # "buy" o "sell"
        self.market = market          # datos del mercado
        self.outcome = outcome        # "yes" o "no"
        self.confidence = confidence  # 0.0 a 1.0
        self.reason = reason          # explicación
        self.amount_pct = amount_pct  # % del capital a usar

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "market_id": self.market.get("id", ""),
            "market_name": self.market.get("question", ""),
            "outcome": self.outcome,
            "confidence": self.confidence,
            "reason": self.reason,
            "amount_pct": self.amount_pct,
        }

    def __repr__(self):
        return (
            f"Signal({self.action} {self.outcome} | "
            f"conf={self.confidence:.2f} | {self.reason})"
        )


class BaseStrategy(ABC):
    """
    Clase base para todas las estrategias.
    Cada estrategia implementa analyze() y genera señales.
    """

    def __init__(self, config: dict):
        self.config = config
        self.name = self.__class__.__name__
        self.enabled = config.get("enabled", True)
        self.weight = config.get("weight", 1.0)

    @abstractmethod
    def analyze(self, market: dict, price_history: list[dict],
                market_data_service=None) -> Optional[Signal]:
        """
        Analiza un mercado y retorna una señal o None.

        Args:
            market: datos del mercado
            price_history: historial de precios
            market_data_service: servicio de datos para análisis adicional

        Returns:
            Signal si hay oportunidad, None si no
        """
        pass

    @abstractmethod
    def should_close(self, trade: dict, current_price: float,
                     price_history: list[dict]) -> bool:
        """
        Determina si se debe cerrar una posición abierta.

        Args:
            trade: datos del trade abierto
            current_price: precio actual
            price_history: historial de precios

        Returns:
            True si se debe cerrar
        """
        pass

    def get_position_size(self, confidence: float,
                          base_pct: float = 5.0) -> float:
        """
        Calcula el tamaño de posición basado en confianza.
        Mayor confianza = mayor posición (con límites).
        """
        # Escalar entre 2% y base_pct según confianza
        min_pct = 2.0
        size = min_pct + (base_pct - min_pct) * confidence
        return round(size, 2)

    def _log(self, message: str, level: str = "info"):
        """Log con nombre de estrategia."""
        getattr(logger, level)(f"[{self.name}] {message}")
