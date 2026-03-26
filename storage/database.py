"""
Gestión de base de datos SQLite.
Persistencia de trades, logs y estadísticas.
"""

import os
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session
from loguru import logger

from .models import Base, Trade, BotLog, DailyStats

DB_PATH = "data/polybot.db"
_engine = None
_SessionLocal = None


def init_db():
    """Inicializa la base de datos y crea las tablas."""
    global _engine, _SessionLocal

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    _engine = create_engine(
        f"sqlite:///{DB_PATH}",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(_engine)
    _SessionLocal = sessionmaker(bind=_engine)

    logger.info(f"Base de datos inicializada: {DB_PATH}")


def get_session() -> Session:
    """Obtiene una sesión de base de datos."""
    if _SessionLocal is None:
        init_db()
    return _SessionLocal()


class TradeRepository:
    """Repositorio para operaciones con trades."""

    @staticmethod
    def save_trade(trade_data: dict) -> Trade:
        """Guarda un nuevo trade."""
        session = get_session()
        try:
            trade = Trade(**trade_data)
            session.add(trade)
            session.commit()
            session.refresh(trade)
            logger.info(f"Trade guardado: {trade.trade_id}")
            return trade
        except Exception as e:
            session.rollback()
            logger.error(f"Error guardando trade: {e}")
            raise
        finally:
            session.close()

    @staticmethod
    def update_trade(trade_id: str, updates: dict) -> Optional[Trade]:
        """Actualiza un trade existente."""
        session = get_session()
        try:
            trade = (
                session.query(Trade)
                .filter(Trade.trade_id == trade_id)
                .first()
            )
            if trade:
                for key, value in updates.items():
                    if hasattr(trade, key):
                        setattr(trade, key, value)
                session.commit()
                session.refresh(trade)
                logger.info(f"Trade actualizado: {trade_id}")
            return trade
        except Exception as e:
            session.rollback()
            logger.error(f"Error actualizando trade: {e}")
            raise
        finally:
            session.close()

    @staticmethod
    def close_trade(trade_id: str, exit_price: float,
                    pnl: float, pnl_pct: float) -> Optional[Trade]:
        """Cierra un trade con precio de salida y P&L."""
        return TradeRepository.update_trade(trade_id, {
            "exit_price": exit_price,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "status": "closed",
            "closed_at": datetime.now(timezone.utc),
        })

    @staticmethod
    def get_open_trades(mode: str = "paper") -> list[Trade]:
        """Obtiene todos los trades abiertos."""
        session = get_session()
        try:
            trades = (
                session.query(Trade)
                .filter(Trade.status == "open", Trade.mode == mode)
                .order_by(desc(Trade.timestamp))
                .all()
            )
            return [t.to_dict() for t in trades]
        finally:
            session.close()

    @staticmethod
    def get_all_trades(mode: str = "paper",
                       limit: int = 100) -> list[dict]:
        """Obtiene todos los trades."""
        session = get_session()
        try:
            trades = (
                session.query(Trade)
                .filter(Trade.mode == mode)
                .order_by(desc(Trade.timestamp))
                .limit(limit)
                .all()
            )
            return [t.to_dict() for t in trades]
        finally:
            session.close()

    @staticmethod
    def get_closed_trades(mode: str = "paper",
                          limit: int = 100) -> list[dict]:
        """Obtiene trades cerrados."""
        session = get_session()
        try:
            trades = (
                session.query(Trade)
                .filter(Trade.status == "closed", Trade.mode == mode)
                .order_by(desc(Trade.closed_at))
                .limit(limit)
                .all()
            )
            return [t.to_dict() for t in trades]
        finally:
            session.close()

    @staticmethod
    def get_stats(mode: str = "paper") -> dict:
        """Calcula estadísticas generales."""
        session = get_session()
        try:
            closed = (
                session.query(Trade)
                .filter(Trade.status == "closed", Trade.mode == mode)
                .all()
            )

            if not closed:
                return {
                    "total_trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "win_rate": 0.0,
                    "total_pnl": 0.0,
                    "avg_pnl": 0.0,
                    "best_trade": 0.0,
                    "worst_trade": 0.0,
                    "avg_win": 0.0,
                    "avg_loss": 0.0,
                    "profit_factor": 0.0,
                }

            total = len(closed)
            wins = [t for t in closed if t.pnl > 0]
            losses = [t for t in closed if t.pnl <= 0]
            pnls = [t.pnl for t in closed]

            total_wins = sum(t.pnl for t in wins) if wins else 0
            total_losses = abs(sum(t.pnl for t in losses)) if losses else 0

            return {
                "total_trades": total,
                "wins": len(wins),
                "losses": len(losses),
                "win_rate": (len(wins) / total * 100) if total > 0 else 0,
                "total_pnl": sum(pnls),
                "avg_pnl": sum(pnls) / total if total > 0 else 0,
                "best_trade": max(pnls) if pnls else 0,
                "worst_trade": min(pnls) if pnls else 0,
                "avg_win": (
                    total_wins / len(wins) if wins else 0
                ),
                "avg_loss": (
                    -total_losses / len(losses) if losses else 0
                ),
                "profit_factor": (
                    total_wins / total_losses
                    if total_losses > 0
                    else float("inf")
                ),
            }
        finally:
            session.close()

    @staticmethod
    def get_equity_curve(mode: str = "paper",
                         initial_capital: float = 1000.0) -> list[dict]:
        """Genera la curva de equity para gráficas."""
        session = get_session()
        try:
            trades = (
                session.query(Trade)
                .filter(Trade.status == "closed", Trade.mode == mode)
                .order_by(Trade.closed_at)
                .all()
            )

            curve = [{"timestamp": None, "equity": initial_capital}]
            equity = initial_capital

            for trade in trades:
                equity += trade.pnl
                curve.append({
                    "timestamp": (
                        trade.closed_at.isoformat()
                        if trade.closed_at else None
                    ),
                    "equity": round(equity, 2),
                })

            return curve
        finally:
            session.close()


class LogRepository:
    """Repositorio para logs del bot."""

    @staticmethod
    def add_log(level: str, module: str, message: str):
        """Añade un log a la base de datos."""
        session = get_session()
        try:
            log = BotLog(level=level, module=module, message=message)
            session.add(log)
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

    @staticmethod
    def get_logs(limit: int = 200, level: Optional[str] = None) -> list[dict]:
        """Obtiene los últimos logs."""
        session = get_session()
        try:
            query = session.query(BotLog)
            if level:
                query = query.filter(BotLog.level == level)
            logs = (
                query.order_by(desc(BotLog.timestamp))
                .limit(limit)
                .all()
            )
            return [log.to_dict() for log in logs]
        finally:
            session.close()

    @staticmethod
    def clear_old_logs(days: int = 30):
        """Elimina logs antiguos."""
        session = get_session()
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            (
                session.query(BotLog)
                .filter(BotLog.timestamp < cutoff)
                .delete()
            )
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()
