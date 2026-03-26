"""Utilidades generales."""

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Any


def generate_trade_id() -> str:
    """Genera un ID único para un trade."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    random_part = secrets.token_hex(4)
    return f"T-{timestamp}-{random_part}"


def format_currency(amount: float, decimals: int = 2) -> str:
    """Formatea un número como moneda."""
    return f"${amount:,.{decimals}f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """Formatea un número como porcentaje."""
    return f"{value:+.{decimals}f}%"


def timestamp_now() -> str:
    """Retorna timestamp actual ISO."""
    return datetime.now(timezone.utc).isoformat()


def calculate_pnl(entry_price: float, exit_price: float,
                  quantity: float, side: str) -> float:
    """Calcula P&L de un trade."""
    if side == "buy":
        return (exit_price - entry_price) * quantity
    else:
        return (entry_price - exit_price) * quantity


def calculate_pnl_pct(entry_price: float, exit_price: float,
                      side: str) -> float:
    """Calcula P&L porcentual."""
    if entry_price == 0:
        return 0.0
    if side == "buy":
        return ((exit_price - entry_price) / entry_price) * 100
    else:
        return ((entry_price - exit_price) / entry_price) * 100


def safe_divide(a: float, b: float, default: float = 0.0) -> float:
    """División segura que evita ZeroDivisionError."""
    return a / b if b != 0 else default
