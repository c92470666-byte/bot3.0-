"""
Gestión de Portafolio.
Rastrea capital, posiciones y rendimiento.
"""

from datetime import datetime, timezone
from typing import Optional
from loguru import logger

from storage.database import TradeRepository


class Portfolio:
    """
    Gestiona el estado del portafolio.
    Rastrea capital disponible, posiciones abiertas y métricas.
    """

    def __init__(self, initial_capital: float, mode: str = "paper"):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.mode = mode
        self.trade_repo = TradeRepository()

    def get_available_capital(self) -> float:
        """Capital disponible (no comprometido en posiciones)."""
        open_trades = self.trade_repo.get_open_trades(self.mode)
        committed = sum(t.get("cost", 0) for t in open_trades)
        return max(0, self.capital - committed)

    def get_total_value(self) -> float:
        """Valor total del portafolio (capital + posiciones abiertas)."""
        open_trades = self.trade_repo.get_open_trades(self.mode)
        positions_value = sum(t.get("cost", 0) for t in open_trades)
        return self.capital + positions_value

    def update_capital_after_buy(self, cost: float):
        """Actualiza capital después de una compra."""
        self.capital -= cost
        logger.debug(f"Capital después de compra: ${self.capital:.2f}")

    def update_capital_after_sell(self, cost: float, pnl: float):
        """Actualiza capital después de una venta."""
        self.capital += cost + pnl
        logger.debug(
            f"Capital después de venta: ${self.capital:.2f} "
            f"(P&L: ${pnl:+.2f})"
        )

    def get_open_positions(self) -> list[dict]:
        """Obtiene todas las posiciones abiertas."""
        return self.trade_repo.get_open_trades(self.mode)

    def get_position_count(self) -> int:
        """Número de posiciones abiertas."""
        return len(self.trade_repo.get_open_trades(self.mode))

    def get_performance(self) -> dict:
        """Calcula métricas de rendimiento del portafolio."""
        stats = self.trade_repo.get_stats(self.mode)
        equity_curve = self.trade_repo.get_equity_curve(
            self.mode, self.initial_capital
        )

        current_equity = (
            equity_curve[-1]["equity"] if equity_curve else self.initial_capital
        )
        total_return = (
            ((current_equity - self.initial_capital) / self.initial_capital)
            * 100
        )

        # Calcular max drawdown
        max_drawdown = self._calculate_max_drawdown(equity_curve)

        return {
            "initial_capital": self.initial_capital,
            "current_capital": round(self.capital, 2),
            "current_equity": round(current_equity, 2),
            "available_capital": round(self.get_available_capital(), 2),
            "total_return_pct": round(total_return, 2),
            "total_pnl": round(stats.get("total_pnl", 0), 2),
            "total_trades": stats.get("total_trades", 0),
            "wins": stats.get("wins", 0),
            "losses": stats.get("losses", 0),
            "win_rate": round(stats.get("win_rate", 0), 2),
            "avg_pnl": round(stats.get("avg_pnl", 0), 2),
            "best_trade": round(stats.get("best_trade", 0), 2),
            "worst_trade": round(stats.get("worst_trade", 0), 2),
            "profit_factor": round(stats.get("profit_factor", 0), 2),
            "max_drawdown": round(max_drawdown, 2),
            "open_positions": self.get_position_count(),
        }

    def _calculate_max_drawdown(self, equity_curve: list[dict]) -> float:
        """Calcula el máximo drawdown de la curva de equity."""
        if len(equity_curve) < 2:
            return 0.0

        peak = equity_curve[0]["equity"]
        max_dd = 0.0

        for point in equity_curve:
            equity = point["equity"]
            if equity > peak:
                peak = equity
            dd = ((peak - equity) / peak) * 100 if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

        return max_dd

    def get_summary_text(self) -> str:
        """Genera un resumen en texto para Telegram."""
        perf = self.get_performance()
        return (
            f"📊 *Resumen del Portafolio*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Capital inicial: ${perf['initial_capital']:,.2f}\n"
            f"💵 Capital actual: ${perf['current_equity']:,.2f}\n"
            f"📈 Retorno: {perf['total_return_pct']:+.2f}%\n"
            f"💹 P&L Total: ${perf['total_pnl']:+.2f}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 Trades totales: {perf['total_trades']}\n"
            f"✅ Ganados: {perf['wins']}\n"
            f"❌ Perdidos: {perf['losses']}\n"
            f"🎯 Win Rate: {perf['win_rate']:.1f}%\n"
            f"📉 Max Drawdown: {perf['max_drawdown']:.2f}%\n"
            f"📂 Posiciones abiertas: {perf['open_positions']}\n"
        )
