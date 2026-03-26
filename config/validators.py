"""
Validación de configuración.
Garantiza que el usuario no pueda introducir valores peligrosos.
"""

from typing import Any


class ConfigValidator:
    """Valida la configuración antes de guardarla."""

    def validate(self, config: dict) -> list[str]:
        """
        Valida un diccionario de configuración.
        Retorna lista de errores (vacía si todo OK).
        """
        errors = []

        # Validar modo
        if "mode" in config:
            if config["mode"] not in ("paper", "real"):
                errors.append("El modo debe ser 'paper' o 'real'")

        # Validar capital
        if "capital_initial" in config:
            try:
                cap = float(config["capital_initial"])
                if cap <= 0:
                    errors.append("El capital inicial debe ser mayor a 0")
                if cap > 1_000_000:
                    errors.append("Capital máximo permitido: 1,000,000")
            except (ValueError, TypeError):
                errors.append("El capital inicial debe ser un número válido")

        # Validar riesgo
        risk = config.get("risk", {})
        if risk:
            errors.extend(self._validate_risk(risk))

        # Validar ejecución
        execution = config.get("execution", {})
        if execution:
            errors.extend(self._validate_execution(execution))

        # Validar Telegram
        telegram = config.get("telegram", {})
        if telegram:
            errors.extend(self._validate_telegram(telegram))

        # Validar API keys para modo real
        if config.get("mode") == "real":
            api = config.get("api", {})
            if not api.get("key") or not api.get("secret"):
                errors.append(
                    "API Key y Secret son obligatorios para modo REAL"
                )

        return errors

    def _validate_risk(self, risk: dict) -> list[str]:
        """Valida parámetros de riesgo."""
        errors = []

        numeric_fields = {
            "max_position_pct": (0.1, 100, "Máx. posición (%)"),
            "max_total_exposure_pct": (1, 100, "Máx. exposición total (%)"),
            "stop_loss_pct": (0.1, 50, "Stop Loss (%)"),
            "take_profit_pct": (0.1, 500, "Take Profit (%)"),
            "max_daily_loss_pct": (0.1, 50, "Máx. pérdida diaria (%)"),
        }

        for field, (min_val, max_val, label) in numeric_fields.items():
            if field in risk:
                try:
                    val = float(risk[field])
                    if val < min_val or val > max_val:
                        errors.append(
                            f"{label} debe estar entre {min_val} y {max_val}"
                        )
                except (ValueError, TypeError):
                    errors.append(f"{label} debe ser un número válido")

        if "max_trades_per_day" in risk:
            try:
                val = int(risk["max_trades_per_day"])
                if val < 1 or val > 100:
                    errors.append("Máx. trades/día debe estar entre 1 y 100")
            except (ValueError, TypeError):
                errors.append("Máx. trades/día debe ser un número entero")

        return errors

    def _validate_execution(self, execution: dict) -> list[str]:
        """Valida parámetros de ejecución."""
        errors = []

        if "interval_seconds" in execution:
            try:
                val = int(execution["interval_seconds"])
                if val < 30:
                    errors.append("Intervalo mínimo: 30 segundos")
                if val > 86400:
                    errors.append("Intervalo máximo: 86400 segundos (24h)")
            except (ValueError, TypeError):
                errors.append("El intervalo debe ser un número entero")

        if "slippage_tolerance_pct" in execution:
            try:
                val = float(execution["slippage_tolerance_pct"])
                if val < 0 or val > 10:
                    errors.append("Tolerancia de slippage: entre 0% y 10%")
            except (ValueError, TypeError):
                errors.append("Slippage debe ser un número válido")

        return errors

    def _validate_telegram(self, telegram: dict) -> list[str]:
        """Valida configuración de Telegram."""
        errors = []

        if telegram.get("enabled"):
            if not telegram.get("token"):
                errors.append("Token de Telegram requerido si está activado")
            elif len(telegram["token"]) < 20:
                errors.append("Token de Telegram parece inválido")

        return errors
