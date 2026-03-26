"""
Rutas de configuración.
Formulario principal para configurar el bot sin tocar código.
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from loguru import logger

config_bp = Blueprint("config", __name__, url_prefix="/config")


@config_bp.route("/", methods=["GET"])
def config_page():
    """Página del formulario de configuración."""
    from dashboard.app import get_config_manager
    config = get_config_manager().get_all()
    return render_template("config.html", config=config)


@config_bp.route("/save", methods=["POST"])
def save_config():
    """
    Guarda la configuración desde el formulario.
    Acepta tanto form data como JSON.
    """
    from dashboard.app import get_config_manager
    cm = get_config_manager()

    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = _parse_form_data(request.form)

        success, errors = cm.update(data)

        if request.is_json:
            if success:
                return jsonify({
                    "success": True,
                    "message": "Configuración guardada correctamente"
                })
            else:
                return jsonify({
                    "success": False,
                    "errors": errors
                }), 400
        else:
            if success:
                return redirect(url_for("config.config_page") + "?saved=1")
            else:
                config = cm.get_all()
                return render_template(
                    "config.html",
                    config=config,
                    errors=errors
                )

    except Exception as e:
        logger.error(f"Error guardando configuración: {e}")
        if request.is_json:
            return jsonify({
                "success": False,
                "errors": [str(e)]
            }), 500
        return redirect(url_for("config.config_page") + "?error=1")


@config_bp.route("/reset", methods=["POST"])
def reset_config():
    """Resetea la configuración a valores por defecto."""
    from dashboard.app import get_config_manager
    cm = get_config_manager()
    cm.reset_to_defaults()

    if request.is_json:
        return jsonify({
            "success": True,
            "message": "Configuración reseteada a valores por defecto"
        })
    return redirect(url_for("config.config_page") + "?reset=1")


@config_bp.route("/test-api", methods=["POST"])
def test_api():
    """Prueba la conexión con la API de Polymarket."""
    from dashboard.app import get_engine
    engine = get_engine()

    if engine:
        result = engine.client.test_connection()
        return jsonify(result)

    return jsonify({"success": False, "message": "Motor no disponible"})


@config_bp.route("/test-telegram", methods=["POST"])
def test_telegram():
    """Envía un mensaje de prueba por Telegram."""
    from dashboard.app import get_config_manager
    cm = get_config_manager()
    config = cm.get_all()

    token = config.get("telegram", {}).get("token", "")
    chat_id = config.get("telegram", {}).get("chat_id", "")

    if not token or not chat_id:
        return jsonify({
            "success": False,
            "message": "Token y Chat ID requeridos"
        })

    try:
        import requests
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(url, json={
            "chat_id": chat_id,
            "text": "✅ PolyBot: Conexión de Telegram verificada correctamente!",
            "parse_mode": "Markdown",
        }, timeout=10)

        if resp.status_code == 200:
            return jsonify({
                "success": True,
                "message": "Mensaje de prueba enviado"
            })
        else:
            return jsonify({
                "success": False,
                "message": f"Error: {resp.text}"
            })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        })


def _parse_form_data(form) -> dict:
    """
    Convierte datos del formulario HTML a estructura de config.
    Mapea campos planos a estructura anidada.
    """
    data = {}

    # Modo
    if "mode" in form:
        data["mode"] = form["mode"]

    # Capital
    if "capital_initial" in form:
        try:
            data["capital_initial"] = float(form["capital_initial"])
        except ValueError:
            pass

    # API
    api = {}
    if "api_key" in form and form["api_key"]:
        api["key"] = form["api_key"]
    if "api_secret" in form and form["api_secret"]:
        api["secret"] = form["api_secret"]
    if "api_passphrase" in form and form["api_passphrase"]:
        api["passphrase"] = form["api_passphrase"]
    if api:
        data["api"] = api

    # Mercados
    markets = {}
    selected = form.getlist("markets_selected")
    if selected:
        markets["selected"] = selected
    if "markets_max" in form:
        try:
            markets["max_markets"] = int(form["markets_max"])
        except ValueError:
            pass
    if "markets_min_liquidity" in form:
        try:
            markets["min_liquidity"] = float(form["markets_min_liquidity"])
        except ValueError:
            pass
    if markets:
        data["markets"] = markets

    # Estrategias
    strategies = {}
    active = form.getlist("strategies_active")
    if active:
        strategies["active"] = active
    if strategies:
        data["strategies"] = strategies

    # Riesgo
    risk = {}
    risk_fields = {
        "risk_max_position": ("max_position_pct", float),
        "risk_max_exposure": ("max_total_exposure_pct", float),
        "risk_stop_loss": ("stop_loss_pct", float),
        "risk_take_profit": ("take_profit_pct", float),
        "risk_max_daily_loss": ("max_daily_loss_pct", float),
        "risk_max_trades": ("max_trades_per_day", int),
    }
    for form_key, (config_key, type_fn) in risk_fields.items():
        if form_key in form:
            try:
                risk[config_key] = type_fn(form[form_key])
            except ValueError:
                pass
    if risk:
        data["risk"] = risk

    # Ejecución
    execution = {}
    if "execution_interval" in form:
        try:
            execution["interval_seconds"] = int(form["execution_interval"])
        except ValueError:
            pass
    if "execution_slippage" in form:
        try:
            execution["slippage_tolerance_pct"] = float(
                form["execution_slippage"]
            )
        except ValueError:
            pass
    if execution:
        data["execution"] = execution

    # Telegram
    telegram = {}
    telegram["enabled"] = "telegram_enabled" in form
    if "telegram_token" in form:
        telegram["token"] = form["telegram_token"]
    if "telegram_chat_id" in form:
        telegram["chat_id"] = form["telegram_chat_id"]
    telegram["notify_trades"] = "telegram_notify_trades" in form
    telegram["notify_errors"] = "telegram_notify_errors" in form
    telegram["notify_daily_summary"] = "telegram_notify_daily" in form
    data["telegram"] = telegram

    return data
