"""
Sistema de notificaciones por Telegram.
Envía alertas de trades, errores y resúmenes.
"""

import asyncio
from typing import Optional
from loguru import logger


class NotificationService:
    """Servicio de notificaciones asíncronas."""

    def __init__(self, telegram_bot=None):
        self.bot = telegram_bot
        self._queue: list[str] = []

    def set_bot(self, bot):
        """Establece el bot de Telegram."""
        self.bot = bot

    def notify_trade_opened(self, trade: dict):
        """Notifica apertura de trade."""
        msg = (
            f"🔵 *Nuevo Trade Abierto*\n\n"
            f"📌 {trade.get('market_name', '')[:80]}\n"
            f"📊 {trade.get('side', '').upper()} "
            f"{trade.get('outcome', '').upper()}\n"
            f"💲 Precio: {trade.get('entry_price', 0):.4f}\n"
            f"💰 Costo: ${trade.get('cost', 0):.2f}\n"
            f"🎯 Estrategia: {trade.get('strategy', 'N/A')[:50]}\n"
            f"🏷️ ID: `{trade.get('trade_id', '')}`"
        )
        self._send(msg)

    def notify_trade_closed(self, trade: dict):
        """Notifica cierre de trade."""
        pnl = trade.get("pnl", 0)
        emoji = "✅" if pnl >= 0 else "❌"

        msg = (
            f"{emoji} *Trade Cerrado*\n\n"
            f"📌 {trade.get('market_name', '')[:80]}\n"
            f"💲 Entrada: {trade.get('entry_price', 0):.4f}\n"
            f"💲 Salida: {trade.get('exit_price', 0):.4f}\n"
            f"💹 P&L: ${pnl:+.2f} ({trade.get('pnl_pct', 0):+.2f}%)\n"
            f"🏷️ ID: `{trade.get('trade_id', '')}`"
        )
        self._send(msg)

    def notify_error(self, error_message: str):
        """Notifica un error."""
        msg = f"🚨 *Error del Bot*\n\n{error_message}"
        self._send(msg)

    def notify_daily_summary(self, summary: dict):
        """Envía resumen diario."""
        msg = (
            f"📊 *Resumen Diario*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 Fecha: {summary.get('date', 'N/A')}\n"
            f"📋 Trades: {summary.get('trades_today', 0)}\n"
            f"💹 P&L: ${summary.get('daily_pnl', 0):+.2f}\n"
        )
        self._send(msg)

    def _send(self, message: str):
        """Envía mensaje de forma asíncrona."""
        if not self.bot:
            return

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(
                    self.bot.send_notification(message)
                )
            else:
                loop.run_until_complete(
                    self.bot.send_notification(message)
                )
        except RuntimeError:
            # Si no hay event loop, crear uno temporal
            try:
                new_loop = asyncio.new_event_loop()
                new_loop.run_until_complete(
                    self.bot.send_notification(message)
                )
                new_loop.close()
            except Exception as e:
                logger.error(f"Error enviando notificación: {e}")
