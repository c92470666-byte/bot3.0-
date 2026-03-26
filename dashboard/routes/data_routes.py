"""
Rutas de datos y API interna.
Provee datos para gráficas y tablas del dashboard.
"""

from flask import Blueprint, jsonify, request
from loguru import logger

from storage.database import TradeRepository, LogRepository

data_bp = Blueprint("data", __name__, url_prefix="/api")


@data_bp.route("/trades", methods=["GET"])
def get_trades():
    """Obtiene historial de trades."""
    mode = request.args.get("mode", "paper")
    limit = int(request.args.get("limit", 100))
    status = request.args.get("status", "all")

    if status == "open":
        trades = TradeRepository.get_open_trades(mode)
    elif status == "closed":
        trades = TradeRepository.get_closed_trades(mode, limit)
    else:
        trades = TradeRepository.get_all_trades(mode, limit)

    return jsonify(trades)


@data_bp.route("/stats", methods=["GET"])
def get_stats():
    """Obtiene estadísticas generales."""
    mode = request.args.get("mode", "paper")
    stats = TradeRepository.get_stats(mode)
    return jsonify(stats)


@data_bp.route("/equity-curve", methods=["GET"])
def get_equity_curve():
    """Obtiene datos para la curva de equity."""
    from dashboard.app import get_config_manager

    mode = request.args.get("mode", "paper")
    config = get_config_manager().get_all()
    initial = config.get("capital_initial", 1000.0)

    curve = TradeRepository.get_equity_curve(mode, initial)
    return jsonify(curve)


@data_bp.route("/logs", methods=["GET"])
def get_logs():
    """Obtiene logs del sistema."""
    limit = int(request.args.get("limit", 200))
    level = request.args.get("level", None)

    logs = LogRepository.get_logs(limit=limit, level=level)
    return jsonify(logs)


@data_bp.route("/performance", methods=["GET"])
def get_performance():
    """Obtiene métricas de rendimiento completas."""
    from dashboard.app import get_engine

    engine = get_engine()
    if not engine:
        return jsonify({"error": "Motor no disponible"}), 500

    perf = engine.portfolio.get_performance()
    return jsonify(perf)


@data_bp.route("/daily-stats", methods=["GET"])
def get_daily_stats():
    """Obtiene estadísticas diarias."""
    from dashboard.app import get_engine

    engine = get_engine()
    if not engine:
        return jsonify({"error": "Motor no disponible"}), 500

    daily = engine.risk_manager.get_daily_summary()
    return jsonify(daily)


@data_bp.route("/export/trades", methods=["GET"])
def export_trades():
    """Exporta trades a CSV."""
    import csv
    import io
    from flask import Response

    mode = request.args.get("mode", "paper")
    trades = TradeRepository.get_all_trades(mode=mode, limit=10000)

    if not trades:
        return jsonify({"message": "No hay trades para exportar"}), 404

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=trades[0].keys())
    writer.writeheader()
    writer.writerows(trades)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=polybot_trades_{mode}.csv"
        },
    )
