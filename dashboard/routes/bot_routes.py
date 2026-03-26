"""
Rutas de control del bot.
Iniciar, detener, estado.
"""

from flask import Blueprint, jsonify, request, render_template
from loguru import logger

bot_bp = Blueprint("bot", __name__, url_prefix="/bot")


@bot_bp.route("/start", methods=["POST"])
def start_bot():
    """Inicia el bot de trading."""
    from dashboard.app import get_engine, get_config_manager

    engine = get_engine()
    config = get_config_manager().get_all()

    if not engine:
        return jsonify({
            "success": False,
            "message": "Motor no disponible"
        }), 500

    # Verificar modo real
    if config.get("mode") == "real":
        confirmation = None
        if request.is_json:
            confirmation = request.get_json().get("confirmation", "")
        else:
            confirmation = request.form.get("confirmation", "")

        if confirmation != "CONFIRMAR":
            return jsonify({
                "success": False,
                "message": (
                    "⚠️ Estás a punto de usar DINERO REAL. "
                    "Escribe 'CONFIRMAR' para continuar."
                ),
                "requires_confirmation": True,
            }), 400

    result = engine.start()
    status_code = 200 if result["success"] else 400
    return jsonify(result), status_code


@bot_bp.route("/stop", methods=["POST"])
def stop_bot():
    """Detiene el bot de trading."""
    from dashboard.app import get_engine

    engine = get_engine()
    if not engine:
        return jsonify({
            "success": False,
            "message": "Motor no disponible"
        }), 500

    result = engine.stop()
    return jsonify(result)


@bot_bp.route("/status", methods=["GET"])
def bot_status():
    """Obtiene el estado actual del bot."""
    from dashboard.app import get_engine

    engine = get_engine()
    if not engine:
        return jsonify({"status": "unavailable"})

    return jsonify(engine.get_status())


@bot_bp.route("/markets", methods=["GET"])
def get_markets():
    """Obtiene mercados disponibles."""
    from dashboard.app import get_engine

    engine = get_engine()
    if not engine:
        return jsonify([])

    category = request.args.get("category", "crypto")
    limit = int(request.args.get("limit", 20))

    markets = engine.market_data.get_markets_by_category(
        category=category, limit=limit
    )
    return jsonify(markets)
