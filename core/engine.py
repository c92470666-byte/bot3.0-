"""
Motor Principal del Bot.
Orquesta estrategias, riesgo y ejecución.
"""

import time
import threading
from datetime import datetime, timezone
from typing import Optional
from loguru import logger

from config.settings import ConfigManager
from api.polymarket_client import PolymarketClient
from api.market_data import MarketDataService
from api.order_manager import OrderManager
from core.risk_manager import RiskManager
from core.portfolio import Portfolio
from core.strategies import get_strategy, STRATEGIES
from storage.database import TradeRepository, LogRepository


class TradingEngine:
    """
    Motor principal que ejecuta el ciclo de trading.

    Ciclo:
    1. Obtener mercados activos
    2. Recopilar datos de precio
    3. Ejecutar estrategias
    4. Filtrar señales por riesgo
    5. Ejecutar órdenes
    6. Monitorear posiciones abiertas
    7. Aplicar stop loss / take profit
    8. Esperar intervalo y repetir
    """

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.config = config_manager.get_all()

        # Estado del bot
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._status = "stopped"
        self._last_cycle = None
        self._cycle_count = 0
        self._errors = []

        # Componentes
        self._init_components()

        # Escuchar cambios de configuración
        config_manager.on_change(self._on_config_change)

    def _init_components(self):
        """Inicializa todos los componentes del motor."""
        config = self.config

        # Cliente API
        api_config = config.get("api", {})
        self.client = PolymarketClient(
            api_key=api_config.get("key", ""),
            api_secret=api_config.get("secret", ""),
            passphrase=api_config.get("passphrase", ""),
        )

        # Modo
        self.mode = config.get("mode", "paper")

        # Servicios
        self.market_data = MarketDataService(self.client)
        self.order_manager = OrderManager(self.client, self.mode)
        self.risk_manager = RiskManager(config.get("risk", {}))
        self.portfolio = Portfolio(
            initial_capital=config.get("capital_initial", 1000.0),
            mode=self.mode,
        )

        # Estrategias activas
        self.strategies = []
        strategies_config = config.get("strategies", {})
        active_names = strategies_config.get("active", ["momentum"])

        for name in active_names:
            if name in STRATEGIES:
                strat_config = strategies_config.get(name, {})
                strat_config["enabled"] = True
                try:
                    strategy = get_strategy(name, strat_config)
                    self.strategies.append(strategy)
                    logger.info(f"Estrategia cargada: {name}")
                except Exception as e:
                    logger.error(f"Error cargando estrategia {name}: {e}")

        # Intervalo
        self.interval = config.get("execution", {}).get(
            "interval_seconds", 300
        )

        logger.info(
            f"Motor inicializado | Modo: {self.mode} | "
            f"Estrategias: {len(self.strategies)} | "
            f"Intervalo: {self.interval}s"
        )

    def start(self) -> dict:
        """Inicia el bot en un thread separado."""
        if self._running:
            return {"success": False, "message": "El bot ya está corriendo"}

        # Verificar modo real
        if self.mode == "real" and not self.client.is_configured():
            return {
                "success": False,
                "message": (
                    "API Key y Secret requeridos para modo REAL. "
                    "Configúralos en el panel."
                ),
            }

        self._running = True
        self._status = "running"
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        LogRepository.add_log(
            "INFO", "engine",
            f"Bot iniciado en modo {self.mode.upper()}"
        )

        logger.info(f"🟢 Bot INICIADO en modo {self.mode.upper()}")

        return {
            "success": True,
            "message": f"Bot iniciado en modo {self.mode.upper()}",
        }

    def stop(self) -> dict:
        """Detiene el bot."""
        if not self._running:
            return {"success": False, "message": "El bot no está corriendo"}

        self._running = False
        self._status = "stopped"

        LogRepository.add_log("INFO", "engine", "Bot detenido por el usuario")
        logger.info("🔴 Bot DETENIDO")

        return {"success": True, "message": "Bot detenido correctamente"}

    def get_status(self) -> dict:
        """Retorna el estado actual del bot."""
        perf = self.portfolio.get_performance()
        daily = self.risk_manager.get_daily_summary()

        return {
            "status": self._status,
            "mode": self.mode,
            "running": self._running,
            "last_cycle": (
                self._last_cycle.isoformat() if self._last_cycle else None
            ),
            "cycle_count": self._cycle_count,
            "strategies_active": [s.name for s in self.strategies],
            "interval_seconds": self.interval,
            "performance": perf,
            "daily": daily,
            "recent_errors": self._errors[-5:],
        }

    def _run_loop(self):
        """Bucle principal de trading."""
        logger.info("Iniciando bucle de trading...")

        while self._running:
            try:
                self._execute_cycle()
                self._last_cycle = datetime.now(timezone.utc)
                self._cycle_count += 1

                # Esperar intervalo
                for _ in range(self.interval):
                    if not self._running:
                        break
                    time.sleep(1)

            except Exception as e:
                error_msg = f"Error en ciclo de trading: {e}"
                logger.error(error_msg)
                self._errors.append({
                    "timestamp":
                  datetime.now(timezone.utc).isoformat(),
                    "message": error_msg,
                })
                LogRepository.add_log("ERROR", "engine", error_msg)

                # Mantener solo últimos 50 errores
                if len(self._errors) > 50:
                    self._errors = self._errors[-50:]

                # Esperar antes de reintentar
                time.sleep(30)

        logger.info("Bucle de trading finalizado")

    def _execute_cycle(self):
        """Ejecuta un ciclo completo de trading."""
        logger.debug(f"━━━ Ciclo #{self._cycle_count + 1} ━━━")

        # 1. Monitorear posiciones abiertas (stop loss / take profit)
        self._monitor_open_positions()

        # 2. Obtener mercados activos
        categories = self.config.get("markets", {}).get(
            "selected", ["crypto"]
        )
        min_liquidity = self.config.get("markets", {}).get(
            "min_liquidity", 500
        )

        markets = self.market_data.get_all_active_markets(
            categories=categories,
            min_liquidity=min_liquidity,
        )

        if not markets:
            logger.debug("No se encontraron mercados activos")
            return

        logger.debug(f"Mercados encontrados: {len(markets)}")

        # 3. Limitar cantidad de mercados a analizar
        max_markets = self.config.get("markets", {}).get("max_markets", 10)
        # Ordenar por liquidez descendente
        markets.sort(key=lambda m: m.get("liquidity", 0), reverse=True)
        markets = markets[:max_markets]

        # 4. Analizar cada mercado con cada estrategia
        all_signals = []

        for market in markets:
            token_id = market.get("yes_token_id", "")
            if not token_id:
                continue

            # Obtener precio y actualizar historial
            price_data = self.market_data.get_price_with_history(token_id)
            if not price_data:
                continue

            price_history = self.market_data.get_price_history(token_id)

            # Ejecutar cada estrategia
            for strategy in self.strategies:
                if not strategy.enabled:
                    continue

                try:
                    signal = strategy.analyze(
                        market=market,
                        price_history=price_history,
                        market_data_service=self.market_data,
                    )

                    if signal:
                        # Ajustar confianza por peso de la estrategia
                        signal.confidence *= strategy.weight
                        all_signals.append(signal)
                        logger.info(
                            f"📡 Señal: {signal.action.upper()} "
                            f"{signal.outcome.upper()} | "
                            f"Confianza: {signal.confidence:.2f} | "
                            f"{market['question'][:60]}"
                        )

                except Exception as e:
                    logger.error(
                        f"Error en estrategia {strategy.name}: {e}"
                    )

        # 5. Filtrar y ordenar señales
        if not all_signals:
            logger.debug("Sin señales en este ciclo")
            return

        # Ordenar por confianza descendente
        all_signals.sort(key=lambda s: s.confidence, reverse=True)

        # Filtrar confianza mínima
        min_confidence = 0.3
        qualified_signals = [
            s for s in all_signals if s.confidence >= min_confidence
        ]

        logger.info(
            f"Señales calificadas: {len(qualified_signals)}/{len(all_signals)}"
        )

        # 6. Ejecutar señales aprobadas por riesgo
        for signal in qualified_signals:
            self._process_signal(signal)

    def _process_signal(self, signal):
        """Procesa una señal de trading individual."""
        try:
            # Calcular tamaño de posición
            amount = self.risk_manager.calculate_position_size(
                capital=self.portfolio.capital,
                confidence=signal.confidence,
                suggested_pct=signal.amount_pct,
            )

            # Verificar con risk manager
            open_trades = self.portfolio.get_open_positions()
            can_trade, reason = self.risk_manager.can_open_trade(
                capital=self.portfolio.capital,
                amount=amount,
                open_trades=open_trades,
                mode=self.mode,
            )

            if not can_trade:
                logger.info(f"⛔ Trade rechazado por riesgo: {reason}")
                return

            # Verificar que no tengamos ya posición en este mercado
            market_id = signal.market.get("id", "")
            existing = [
                t for t in open_trades
                if t.get("market_id") == market_id
            ]
            if existing:
                logger.debug(
                    f"Ya hay posición abierta en: "
                    f"{signal.market['question'][:40]}"
                )
                return

            # Ejecutar orden
            result = self.order_manager.execute_buy(
                market=signal.market,
                outcome=signal.outcome,
                amount=amount,
                strategy=signal.reason[:100],
            )

            if result:
                self.portfolio.update_capital_after_buy(amount)
                self.risk_manager.register_trade_result(0)  # PnL se registra al cerrar

                LogRepository.add_log(
                    "INFO", "engine",
                    f"BUY {signal.outcome.upper()} ${amount:.2f} | "
                    f"{signal.market['question'][:80]}"
                )

                # Notificar por Telegram si está configurado
                self._notify_trade(result, signal)

        except Exception as e:
            logger.error(f"Error procesando señal: {e}")

    def _monitor_open_positions(self):
        """Monitorea posiciones abiertas para stop loss / take profit."""
        open_trades = self.portfolio.get_open_positions()

        if not open_trades:
            return

        logger.debug(f"Monitoreando {len(open_trades)} posiciones abiertas")

        stop_loss = self.config.get("risk", {}).get("stop_loss_pct", 15.0)
        take_profit = self.config.get("risk", {}).get("take_profit_pct", 25.0)

        for trade in open_trades:
            try:
                token_id = ""
                outcome = trade.get("outcome", "yes")

                # Necesitamos obtener el precio actual
                # En paper mode, simulamos movimiento de precio
                if self.mode == "paper":
                    current_price = self._get_simulated_price(trade)
                else:
                    # En modo real, obtener precio del mercado
                    market_detail = self.client.get_market_detail(
                        trade.get("market_id", "")
                    )
                    if not market_detail:
                        continue
                    tokens = market_detail.get("tokens", [])
                    for token in tokens:
                        if token.get("outcome", "").lower() == outcome:
                            current_price = float(token.get("price", 0))
                            token_id = token.get("token_id", "")
                            break
                    else:
                        continue

                # Verificar stop loss / take profit
                trigger = self.order_manager.check_stop_loss_take_profit(
                    trade_data=trade,
                    current_price=current_price,
                    stop_loss_pct=stop_loss,
                    take_profit_pct=take_profit,
                )

                if trigger:
                    logger.info(
                        f"{'🛑 STOP LOSS' if trigger == 'stop_loss' else '🎯 TAKE PROFIT'} "
                        f"activado para {trade.get('market_name', '')[:50]}"
                    )

                    result = self.order_manager.execute_sell(
                        trade_id=trade["trade_id"],
                        current_price=current_price,
                    )

                    if result:
                        self.portfolio.update_capital_after_sell(
                            trade.get("cost", 0),
                            result.get("pnl", 0),
                        )
                        self.risk_manager.register_trade_result(
                            result.get("pnl", 0)
                        )

                        LogRepository.add_log(
                            "INFO", "engine",
                            f"{trigger.upper()}: "
                            f"P&L ${result['pnl']:+.2f} | "
                            f"{trade.get('market_name', '')[:80]}"
                        )

                # Verificar con estrategia si debe cerrar
                else:
                    price_history = self.market_data.get_price_history(
                        token_id
                    ) if token_id else []

                    for strategy in self.strategies:
                        if strategy.should_close(
                            trade, current_price, price_history
                        ):
                            result = self.order_manager.execute_sell(
                                trade_id=trade["trade_id"],
                                current_price=current_price,
                            )
                            if result:
                                self.portfolio.update_capital_after_sell(
                                    trade.get("cost", 0),
                                    result.get("pnl", 0),
                                )
                                self.risk_manager.register_trade_result(
                                    result.get("pnl", 0)
                                )
                            break

            except Exception as e:
                logger.error(
                    f"Error monitoreando trade "
                    f"{trade.get('trade_id', '?')}: {e}"
                )

    def _get_simulated_price(self, trade: dict) -> float:
        """
        Simula precio actual para paper trading.
        Usa datos reales de la API si están disponibles.
        """
        import random

        entry_price = trade.get("entry_price", 0.5)

        # Intentar obtener precio real
        market_id = trade.get("market_id", "")
        if market_id:
            try:
                market_detail = self.client.get_market_detail(market_id)
                if market_detail:
                    outcome = trade.get("outcome", "yes")
                    tokens = market_detail.get("tokens", [])
                    for token in tokens:
                        if token.get("outcome", "").lower() == outcome:
                            return float(token.get("price", entry_price))
            except Exception:
                pass

        # Fallback: simular con random walk
        change = random.gauss(0, 0.02)  # ±2% desviación
        new_price = entry_price * (1 + change)
        # Mantener entre 0.01 y 0.99
        return max(0.01, min(0.99, new_price))

    def _notify_trade(self, trade_data: dict, signal):
        """Envía notificación de trade por Telegram."""
        # Se implementa en la integración con Telegram
        pass

    def _on_config_change(self, new_config: dict):
        """Callback cuando cambia la configuración."""
        logger.info("Configuración actualizada, recargando componentes...")
        self.config = new_config

        # Actualizar risk manager
        self.risk_manager.update_config(new_config.get("risk", {}))

        # Actualizar intervalo
        self.interval = new_config.get("execution", {}).get(
            "interval_seconds", 300
        )

        # Actualizar modo
        new_mode = new_config.get("mode", "paper")
        if new_mode != self.mode:
            logger.warning(
                f"Modo cambiado: {self.mode} → {new_mode}"
            )
            self.mode = new_mode
            self.order_manager.mode = new_mode
