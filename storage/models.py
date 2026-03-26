"""
Modelos de datos para la base de datos.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, Text, create_engine
)
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class Trade(Base):
    """Modelo para trades ejecutados."""

    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(String(50), unique=True, nullable=False, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    market_id = Column(String(200), nullable=False)
    market_name = Column(String(500))
    side = Column(String(10), nullable=False)  # buy / sell
    outcome = Column(String(10))  # yes / no
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    quantity = Column(Float, nullable=False)
    cost = Column(Float, nullable=False)
    pnl = Column(Float, default=0.0)
    pnl_pct = Column(Float, default=0.0)
    status = Column(String(20), default="open")  # open / closed / cancelled
    strategy = Column(String(50))
    mode = Column(String(10), default="paper")  # paper / real
    notes = Column(Text, default="")
    closed_at = Column(DateTime, nullable=True)

    def to_dict(self) -> dict:
        """Convierte a diccionario."""
        return {
            "id": self.id,
            "trade_id": self.trade_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "market_id": self.market_id,
            "market_name": self.market_name,
            "side": self.side,
            "outcome": self.outcome,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "quantity": self.quantity,
            "cost": self.cost,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
            "status": self.status,
            "strategy": self.strategy,
            "mode": self.mode,
            "notes": self.notes,
            "closed_at": (
                self.closed_at.isoformat() if self.closed_at else None
            ),
        }


class BotLog(Base):
    """Modelo para logs del bot."""

    __tablename__ = "bot_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    level = Column(String(10), default="INFO")
    module = Column(String(50))
    message = Column(Text)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "level": self.level,
            "module": self.module,
            "message": self.message,
        }


class DailyStats(Base):
    """Estadísticas diarias."""

    __tablename__ = "daily_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(10), unique=True, nullable=False)
    trades_count = Column(Integer, default
