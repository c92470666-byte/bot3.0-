"""
Gestor de Riesgo.
Controla exposición, límites y protección del capital.
"""

from datetime import datetime, timezone, date
from typing import Optional
from loguru import logger

from storage.database import TradeRepository


class RiskManager:
    """
    Gestiona el riesgo del portafolio.
    Aplica límites configurados por el usuario.
    """

    def __init__(self, config: dict):
        self.max_position_pct = config.get("max_position_pct", 10.0)
        self.max_total_exposure_pct = config.get("max_total_exposure_pct", 50.0)
        self.stop_loss_pct = config.get("stop_loss_pct", 15.0)
        self.take_profit_pct = config.get("take_profit_pct", 25.0)
        self.max_daily_loss_pct = config.get("max_daily_loss_pct", 5.0)
        self.max_trades_per_day = config.get("max_trades_per_day", 20)
        self._daily_trades = 0
        self._daily_pnl = 0.0
        self._current_date = date.today()

    def can_open_trade(self, capital: float, amount: float,
                       open_trades: list[dict],
                       mode: str = "paper") -> tuple[bool, str]:
        """
        Verifica si se puede abrir un nuevo trade.
        Retorna (permitido, razón).
        """
        self._check_day_reset()

        # 1. Verificar límite de trades diarios
        if self._daily_trades >= self.max_trades_per_day:
            return False, (
                f"Límite diario alcanzado: "
                f"{self._daily_trades}/{self.max_trades_per_day} trades"
            )

        # 2. Verificar pérdida diaria máxima
        daily_loss_limit = capital * (self.max_daily_loss_pct / 100)
        if self._daily_pnl < -daily_loss_limit:
            return False, (
                f"Pérdida diaria máxima alcanzada: "
                f"${self._daily_pnl:.2f} "
                f"(límite: -${daily_loss_limit:.2f})"
            )

        # 3. Verificar tamaño máximo de posición
        max_position = capital * (self.max_position_pct / 100)
        if amount > max_position:
            return False, (
                f"Posición demasiado grande: ${amount:.2f} "
                f"(máx: ${max_position:.2f} = "
                f"{self.max_position_pct}% del capital)"
            )

        # 4. Verificar exposición total
        total_exposure = sum(t.get("cost", 0) for t in open_trades)
        max_exposure = capital * (self.max_total_exposure_pct / 100)

        if total_exposure + amount > max_exposure:
            return False, (
                f"Exposición total excedida: "
                f"${total_exposure + amount:.2f} "
                f"(máx: ${max_exposure:.2f} = "
                f"{self.max_total_exposure_pct}% del capital)"
            )

        # 5. Verificar capital suficiente
        available = capital - total_exposure
        if amount > available:
            return False, (
                f"Capital insuficiente: "
                f"disponible ${available:.2f}, "
                f"requerido ${amount:.2f}"
            )

        return True, "OK"

    def calculate_position_size(self, capital: float,
                                confidence: float,
                                suggested_pct: float) -> float:
        """
        Calcula el tamaño de posición ajustado por riesgo.
        """
        # No exceder máximo por posición
        max_pct = min(suggested_pct, self.max_position_pct)

        # Ajustar por confianza
        adjusted_pct = max_pct * confidence

        # Mínimo 1% del capital
        adjusted_pct = max(adjusted_pct, 1.0)

                amount = capital * (adjusted_pct / 100)

        # Mínimo absoluto $1
        amount = max(amount, 1.0)

        logger.debug(
            f"Position size: {adjusted_pct:.1f}% = ${amount:.2f} "
            f"(confianza: {confidence:.2f})"
        )

        return round(amount, 2)

    def register_trade_result(self, pnl: float):
        """Registra el resultado de un trade para control diario."""
        self._check_day_reset()
        self._daily_trades += 1
        self._daily_pnl += pnl

    def get_daily_summary(self) -> dict:
        """Retorna resumen del día actual."""
        self._check_day_reset()
        return {
            "date": self._current_date.isoformat(),
            "trades_today": self._daily_trades,
            "max_trades": self.max_trades_per_day,
            "daily_pnl": round(self._daily_pnl, 2),
            "trades_remaining": max(
                0, self.max_trades_per_day - self._daily_trades
            ),
        }

    def _check_day_reset(self):
        """Resetea contadores si cambió el día."""
        today = date.today()
        if today != self._current_date:
            logger.info(
                f"Nuevo día: reseteando contadores "
                f"(ayer: {self._daily_trades} trades, "
                f"P&L: ${self._daily_pnl:+.2f})"
            )
            self._daily_trades = 0
            self._daily_pnl = 0.0
            self._current_date = today

    def update_config(self, config: dict):
        """Actualiza la configuración de riesgo en caliente."""
        self.max_position_pct = config.get(
            "max_position_pct", self.max_position_pct
        )
        self.max_total_exposure_pct = config.get(
            "max_total_exposure_pct", self.max_total_exposure_pct
        )
        self.stop_loss_pct = config.get(
            "stop_loss_pct", self.stop_loss_pct
        )
        self.take_profit_pct = config.get(
            "take_profit_pct", self.take_profit_pct
        )
        self.max_daily_loss_pct = config.get(
            "max_daily_loss_pct", self.max_daily_loss_pct
        )
        self.max_trades_per_day = config.get(
            "max_trades_per_day", self.max_trades_per_day
        )
        logger.info("Configuración de riesgo actualizada") 
