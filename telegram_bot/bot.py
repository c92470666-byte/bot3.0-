"""
Bot de Telegram para control remoto.
Permite controlar el bot desde el teléfono.
"""

import asyncio
from typing import Optional
from loguru import logger

try:
    from telegram import Update, BotCommand
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        ContextTypes,
        filters,
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.warning(
        "python-telegram-bot no instalado. "
        "Telegram deshabilitado."
    )


class TelegramBot:
    """
    Bot de Telegram para control remoto del trading bot.

    Comandos:
    /start - Iniciar bot de trading
    /stop - Detener bot de trading
    /status - Estado actual
    /balance - Balance del portafolio
    /trades - Últimas operaciones
    /help - Ayuda
    """

    def __init__(self, config: dict, engine=None):
        self.config = config
        self.engine = engine
        self.token = config.get("telegram", {}).get("token", "")
        self.allowed_chat_id = config.get("telegram", {}).get("chat_id", "")
        self._app: Optional[Application] = None

    def set_engine(self, engine):
        """Establece referencia al motor de trading."""
        self.engine = engine

    def run(self):
        """Inicia el bot de Telegram."""
        if not TELEGRAM_AVAILABLE:
            logger.error("Telegram no disponible")
            return

        if not self.token:
            logger.error("Token de Telegram no configurado")
            return

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._start_bot())
        except Exception as e:
            logger.error(f"Error iniciando Telegram bot: {e}")

    async def _start_bot(self):
        """Configura e inicia el bot async."""
        self._app = (
            Application.builder()
            .token(self.token)
            .build()
        )

        # Registrar comandos
        self._app.add_handler(CommandHandler("start", self._cmd_start))
        self._app.add_handler(CommandHandler("stop", self._cmd_stop))
        self._app.add_handler(CommandHandler("status", self._cmd_status))
        self._app.add_handler(CommandHandler("balance", self._cmd_balance))
        self._app.add_handler(CommandHandler("trades", self._cmd_trades))
        self._app.add_handler(CommandHandler("help", self._cmd_help))
        self._app.add_handler(CommandHandler("performance", self._cmd_performance))

        # Establecer comandos visibles
        commands = [
            BotCommand("start", "▶️ Iniciar bot de trading"),
            BotCommand("stop", "⏹️ Detener bot de trading"),
            BotCommand("status", "📊 Estado actual del bot"),
            BotCommand("balance", "💰 Balance del portafolio"),
            BotCommand("trades", "📋 Últimas operaciones"),
            BotCommand("performance", "📈 Rendimiento detallado"),
            BotCommand("help", "❓ Ayuda"),
        ]

                await self._app.bot.set_my_commands(commands)

        logger.info("Bot de Telegram configurado, iniciando polling...")

        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling(drop_pending_updates=True)

        # Mantener corriendo
        while True:
            await asyncio.sleep(1)

    def _is_authorized(self, update: Update) -> bool:
        """Verifica si el usuario está autorizado."""
        if not self.allowed_chat_id:
            return True  # Sin restricción si no se configura
        return str(update.effective_chat.id) == str(self.allowed_chat_id)

    async def _cmd_start(self, update: Update,
                         context: ContextTypes.DEFAULT_TYPE):
        """Comando /start - Inicia el bot de trading."""
        if not self._is_authorized(update):
            await update.message.reply_text("⛔ No autorizado.")
            return

        if not self.engine:
            await update.message.reply_text(
                "⚠️ Motor de trading no disponible."
            )
            return

        result = self.engine.start()

        if result["success"]:
            await update.message.reply_text(
                f"✅ *Bot Iniciado*\n\n"
                f"🤖 Modo: `{self.engine.mode.upper()}`\n"
                f"📊 Estrategias: {len(self.engine.strategies)}\n"
                f"⏱️ Intervalo: {self.engine.interval}s\n\n"
                f"Usa /status para ver el estado.",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                f"❌ No se pudo iniciar:\n{result['message']}"
            )

    async def _cmd_stop(self, update: Update,
                        context: ContextTypes.DEFAULT_TYPE):
        """Comando /stop - Detiene el bot de trading."""
        if not self._is_authorized(update):
            await update.message.reply_text("⛔ No autorizado.")
            return

        if not self.engine:
            await update.message.reply_text(
                "⚠️ Motor de trading no disponible."
            )
            return

        result = self.engine.stop()
        emoji = "✅" if result["success"] else "❌"
        await update.message.reply_text(f"{emoji} {result['message']}")

    async def _cmd_status(self, update: Update,
                          context: ContextTypes.DEFAULT_TYPE):
        """Comando /status - Estado actual del bot."""
        if not self._is_authorized(update):
            await update.message.reply_text("⛔ No autorizado.")
            return

        if not self.engine:
            await update.message.reply_text(
                "⚠️ Motor de trading no disponible."
            )
            return

        status = self.engine.get_status()
        running_emoji = "🟢" if status["running"] else "🔴"

        text = (
            f"{running_emoji} *Estado del Bot*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 Estado: `{status['status'].upper()}`\n"
            f"🎮 Modo: `{status['mode'].upper()}`\n"
            f"🔄 Ciclos: {status['cycle_count']}\n"
            f"⏱️ Intervalo: {status['interval_seconds']}s\n"
            f"📡 Estrategias: {', '.join(status['strategies_active'])}\n"
        )

        if status.get("last_cycle"):
            text += f"🕐 Último ciclo: `{status['last_cycle'][:19]}`\n"

        # Agregar info diaria
        daily = status.get("daily", {})
        if daily:
            text += (
                f"\n📅 *Hoy*\n"
                f"Trades: {daily.get('trades_today', 0)}"
                f"/{daily.get('max_trades', 20)}\n"
                f"P&L: ${daily.get('daily_pnl', 0):+.2f}\n"
            )

        # Errores recientes
        errors = status.get("recent_errors", [])
        if errors:
            text += f"\n⚠️ Errores recientes: {len(errors)}\n"

        await update.message.reply_text(text, parse_mode="Markdown")

    async def _cmd_balance(self, update: Update,
                           context: ContextTypes.DEFAULT_TYPE):
        """Comando /balance - Balance del portafolio."""
        if not self._is_authorized(update):
            await update.message.reply_text("⛔ No autorizado.")
            return

        if not self.engine:
            await update.message.reply_text(
                "⚠️ Motor de trading no disponible."
            )
            return

        text = self.engine.portfolio.get_summary_text()
        await update.message.reply_text(text, parse_mode="Markdown")

    async def _cmd_trades(self, update: Update,
                          context: ContextTypes.DEFAULT_TYPE):
        """Comando /trades - Últimas operaciones."""
        if not self._is_authorized(update):
            await update.message.reply_text("⛔ No autorizado.")
            return

        from storage.database import TradeRepository
        mode = self.engine.mode if self.engine else "paper"
        trades = TradeRepository.get_all_trades(mode=mode, limit=10)

        if not trades:
            await update.message.reply_text(
                "📋 No hay operaciones registradas aún."
            )
            return

        text = "📋 *Últimas Operaciones*\n━━━━━━━━━━━━━━━━━━━━\n\n"

        for t in trades[:10]:
            status_emoji = {
                "open": "🔵",
                "closed": "✅" if t.get("pnl", 0) >= 0 else "❌",
                "cancelled": "⚪",
            }.get(t.get("status", ""), "⚪")

            pnl_text = ""
            if t.get("status") == "closed":
                pnl_text = f" | P&L: ${t.get('pnl', 0):+.2f}"

            market_name = t.get("market_name", "")[:45]

            text += (
                f"{status_emoji} `{t.get('side', '').upper()} "
                f"{t.get('outcome', '').upper()}`"
                f" @ {t.get('entry_price', 0):.3f}"
                f"{pnl_text}\n"
                f"   📌 {market_name}\n\n"
            )

        await update.message.reply_text(text, parse_mode="Markdown")

    async def _cmd_performance(self, update: Update,
                               context: ContextTypes.DEFAULT_TYPE):
        """Comando /performance - Rendimiento detallado."""
        if not self._is_authorized(update):
            await update.message.reply_text("⛔ No autorizado.")
            return

        if not self.engine:
            await update.message.reply_text(
                "⚠️ Motor de trading no disponible."
            )
            return

        perf = self.engine.portfolio.get_performance()

        text = (
            f"📈 *Rendimiento Detallado*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 Capital inicial: ${perf['initial_capital']:,.2f}\n"
            f"💵 Equity actual: ${perf['current_equity']:,.2f}\n"
            f"📊 Retorno total: {perf['total_return_pct']:+.2f}%\n"
            f"💹 P&L total: ${perf['total_pnl']:+.2f}\n\n"
            f"📋 *Estadísticas*\n"
            f"Total trades: {perf['total_trades']}\n"
            f"✅ Ganados: {perf['wins']}\n"
            f"❌ Perdidos: {perf['losses']}\n"
            f"🎯 Win rate: {perf['win_rate']:.1f}%\n"
            f"📊 P&L promedio: ${perf['avg_pnl']:+.2f}\n"
            f"🏆 Mejor trade: ${perf['best_trade']:+.2f}\n"
            f"💀 Peor trade: ${perf['worst_trade']:+.2f}\n"
            f"⚖️ Profit factor: {perf['profit_factor']:.2f}\n"
            f"📉 Max drawdown: {perf['max_drawdown']:.2f}%\n"
            f"📂 Posiciones abiertas: {perf['open_positions']}\n"
        )

        await update.message.reply_text(text, parse_mode="Markdown")

    async def _cmd_help(self, update: Update,
                        context: ContextTypes.DEFAULT_TYPE):
        """Comando /help - Ayuda."""
        text = (
            "🤖 *PolyBot - Comandos*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "▶️ /start - Iniciar bot de trading\n"
            "⏹️ /stop - Detener bot de trading\n"
            "📊 /status - Estado actual\n"
            "💰 /balance - Balance del portafolio\n"
            "📋 /trades - Últimas operaciones\n"
            "📈 /performance - Rendimiento detallado\n"
            "❓ /help - Esta ayuda\n\n"
            "🌐 *Dashboard web:*\n"
            "Accede al panel completo desde tu navegador\n"
            "para configurar estrategias, riesgo y más."
        )
        await update.message.reply_text(text, parse_mode="Markdown")

    async def send_notification(self, message: str):
        """Envía una notificación proactiva."""
        if not self._app or not self.allowed_chat_id:
            return

        try:
            await self._app.bot.send_message(
                chat_id=self.allowed_chat_id,
                text=message,
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error(f"Error enviando notificación Telegram: {e}") 
