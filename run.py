#!/usr/bin/env python3
"""
PolyBot - Bot de Trading para Polymarket
Punto de entrada principal
"""

import os
import sys
import signal
import threading
from loguru import logger

def setup_logging():
    """Configura el sistema de logging."""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    logger.add(
        "logs/polybot_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level="DEBUG"
    )

def print_banner():
    """Muestra el banner de inicio."""
    banner = """
    ╔══════════════════════════════════════════════╗
    ║                                              ║
    ║   🤖 PolyBot v1.0                           ║
    ║   Bot de Trading para Polymarket             ║
    ║                                              ║
    ║   Dashboard: http://localhost:5000            ║
    ║                                              ║
    ╚══════════════════════════════════════════════╝
    """
    print(banner)

def main():
    """Función principal."""
    setup_logging()
    print_banner()

    # Crear directorios necesarios
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/trades", exist_ok=True)

    # Inicializar base de datos
    from storage.database import init_db
    init_db()

    # Inicializar configuración
    from config.settings import ConfigManager
    config_manager = ConfigManager()
    config = config_manager.load()

    logger.info("Configuración cargada correctamente")
    logger.info(f"Modo: {'PAPER TRADING' if config.get('mode') == 'paper' else '⚠️ REAL'}")

    # Iniciar bot de Telegram si está configurado
    telegram_thread = None
    if config.get("telegram", {}).get("enabled", False):
        from telegram_bot.bot import TelegramBot
        tg_bot = TelegramBot(config)
        telegram_thread = threading.Thread(target=tg_bot.run, daemon=True)
        telegram_thread.start()
        logger.info("Bot de Telegram iniciado")

    # Iniciar dashboard web
    from dashboard.app import create_app
    app = create_app(config_manager)

    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")

    logger.info(f"Dashboard disponible en http://{host}:{port}")

    app.run(
        host=host,
        port=port,
        debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    )

if __name__ == "__main__":
    main()
