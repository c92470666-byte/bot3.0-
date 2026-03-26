"""
Gestor de órdenes.
Abstrae la ejecución de órdenes para modo paper y real.
"""

from datetime import datetime, timezone
from typing import Optional
from loguru import logger

from .polymarket_client import PolymarketClient
from storage.database import TradeRepository
from utils.helpers import generate_trade_id, calculate_pnl, calculate_pnl_pct


class OrderManager:
    """
    Gestiona la ejecución de órdenes.
    Soporta modo paper (simulado) y real.
    """

    def __init__(self, client: PolymarketClient, mode: str = "paper"):
        self.client = client
        self.mode = mode
        self.trade_repo = TradeRepository()

    def execute_buy(self, market: dict, outcome: str,
                    amount: float, strategy: str = "",
                    price: Optional[float] = None) -> Optional[dict]:
        """
        Ejecuta una compra.
        En modo paper: simula la operación.
        En modo real: envía orden a Polymarket.
        """
        token_id = (
            market["yes_token_id"]
            if outcome == "yes"
            else market["no_token_id"]
        )

        # Obtener precio actual si no se especifica
        if price is None:
            price = (
                market["yes_price"]
                if outcome == "yes"
                else market["no_price"]
            )

        if price <= 0 or price >= 1:
            logger.warning(
                f"Precio inválido ({price}) para {market['question'][:50]}"
            )
            return None

        # Calcular cantidad de shares
        quantity = amount / price

        trade_id = generate_trade_id()

        trade_data = {
            "trade_id": trade_id,
            "market_id": market["id"],
            "market_name": market["question"][:500],
            "side": "buy",
            "outcome": outcome,
            "entry_price": price,
            "quantity": quantity,
            "cost": amount,
            "status": "open",
            "strategy": strategy,
            "mode": self.mode,
        }

        if self.mode == "real":
            # Ejecutar orden real
            result = self.client.place_order(
                token_id=token_id,
                side="BUY",
                price=price,
                size=quantity,
            )

            if not result:
                logger.error("Fallo al colocar orden real")
                return None

            trade_data["notes"] = f"Order ID: {result.get('orderID', 'N/A')}"

        # Guardar en base de datos
        trade = self.trade_repo.save_trade(trade_data)

        logger.info(
            f"{'📝 PAPER' if self.mode == 'paper' else '💰 REAL'} BUY: "
            f"{outcome.upper()} @ {price:.4f} | "
            f"Cantidad: {quantity:.2f} | "
            f"Costo: ${amount:.2f} | "
            f"Mercado: {market['question'][:60]}"
        )

        return trade_data

    def execute_sell(self, trade_id: str,
                     current_price: float) -> Optional[dict]:
        """
        Ejecuta una venta (cierra posición).
        """
        session = __import__(
            "storage.database", fromlist=["get_session"]
        ).get_session()

        try:
            from storage.models import Trade
            trade = (
                session.query(Trade)
                .filter(Trade.trade_id == trade_id)
                .first()
            )

            if not trade:
                logger.error(f"Trade no encontrado: {trade_id}")
                return None

            if trade.status != "open":
                logger.warning(f"Trade ya cerrado: {trade_id}")
                return
                          if trade.status != "open":
                logger.warning(f"Trade ya cerrado: {trade_id}")
                return None

            # Calcular P&L
            pnl = calculate_pnl(
                trade.entry_price, current_price,
                trade.quantity, trade.side
            )
            pnl_pct = calculate_pnl_pct(
                trade.entry_price, current_price, trade.side
            )

            if self.mode == "real":
                token_id = ""  # Se obtendría del mercado
                result = self.client.place_order(
                    token_id=token_id,
                    side="SELL",
                    price=current_price,
                    size=trade.quantity,
                )
                if not result:
                    logger.error("Fallo al colocar orden de venta real")
                    return None

            # Cerrar trade en BD
            self.trade_repo.close_trade(
                trade_id=trade_id,
                exit_price=current_price,
                pnl=pnl,
                pnl_pct=pnl_pct,
            )

            result_emoji = "✅" if pnl > 0 else "❌"
            logger.info(
                f"{result_emoji} "
                f"{'📝 PAPER' if self.mode == 'paper' else '💰 REAL'} SELL: "
                f"Exit @ {current_price:.4f} | "
                f"P&L: ${pnl:+.2f} ({pnl_pct:+.2f}%) | "
                f"Mercado: {trade.market_name[:60]}"
            )

            return {
                "trade_id": trade_id,
                "exit_price": current_price,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "status": "closed",
            }

        except Exception as e:
            logger.error(f"Error ejecutando venta: {e}")
            return None
        finally:
            session.close()

    def check_stop_loss_take_profit(
        self, trade_data: dict, current_price: float,
        stop_loss_pct: float, take_profit_pct: float
    ) -> Optional[str]:
        """
        Verifica si se debe cerrar por stop loss o take profit.
        Retorna 'stop_loss', 'take_profit' o None.
        """
        entry = trade_data["entry_price"]
        side = trade_data["side"]

        if side == "buy":
            pnl_pct = ((current_price - entry) / entry) * 100
        else:
            pnl_pct = ((entry - current_price) / entry) * 100

        if pnl_pct <= -stop_loss_pct:
            return "stop_loss"
        elif pnl_pct >= take_profit_pct:
            return "take_profit"

        return None
