"""
Aplicación Flask principal del Dashboard.
Interfaz web completa para configurar y controlar el bot.
"""

import os
from flask import Flask, render_template, redirect, url_for, session, request
from flask_socketio import SocketIO
from loguru import logger

from config.settings import ConfigManager
from core.engine import TradingEngine

socketio = SocketIO()

_config_manager: ConfigManager = None
_engine: TradingEngine = None


def get_engine() -> TradingEngine:
    """Obtiene la instancia del motor de trading."""
    global _engine
    return _engine


def get_config_manager() -> ConfigManager:
    """Obtiene la instancia del config manager."""
    global _config_manager
    return _config_manager


def create_app(config_manager: ConfigManager) -> Flask:
    """
    Factory de la aplicación Flask.
    Crea y configura toda la app web.
    """
    global _config_manager, _engine

    _config_manager = config_manager

    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
    )

    app.secret_key = os.environ.get(
        "FLASK_SECRET_KEY",
        "polybot-secret-change-in-production-2024"
    )

    # Inicializar motor de trading
    _engine = TradingEngine(config_manager)

    # Inicializar SocketIO
    socketio.init_app(app, cors_allowed_origins="*")

    # Registrar rutas
    from dashboard.routes.config_routes import config_bp
    from dashboard.routes.bot_routes import bot_bp
    from dashboard.routes.data_routes import data_bp

    app.register_blueprint(config_bp)
    app.register_blueprint(bot_bp)
    app.register_blueprint(data_bp)

    # Ruta principal
    @app.route("/")
    def index():
        """Dashboard principal."""
        config = config_manager.get_all()
        status = _engine.get_status() if _engine else {}
        return render_template(
            "index.html",
            config=config,
            status=status,
        )

    # Context processor para templates
    @app.context_processor
    def inject_globals():
        return {
            "app_name": "PolyBot",
            "version": "1.0.0",
        }

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template("base.html", error="Página no encontrada"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("base.html", error="Error interno"), 500

    logger.info("Dashboard Flask creado correctamente")
    return app
