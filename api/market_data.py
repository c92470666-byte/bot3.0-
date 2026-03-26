"""
Servicio de datos de mercado.
Cachea datos y proporciona análisis básico.
"""

import time
from datetime import datetime, timezone
from typing import Optional
from loguru import logger

from .polymarket_client import PolymarketClient


class MarketDataService:
    """
    Servicio que gestiona datos de mercado con caché.
    Evita llamadas excesivas a la API.
    """

    def __init__(self, client: PolymarketClient):
        self.client = client
        self._cache: dict = {}
        self._cache_ttl = 60  # segundos
        self._price_history: dict[str, list] = {}

    def get_markets_by_category(self, category: str,
                                limit: int = 20) -> list[dict]:
        """Obtiene mercados filtrados por categoría con caché."""
        cache_key = f"markets_{category}_{limit}"

        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]["data"]

        markets = self.client.get_markets(
            limit=limit, category=category
        )

        # Filtrar por liquidez mínima
        markets = [
            m for m in markets
            if m.get("liquidity", 0) > 100
        ]

        self._update_cache(cache_key, markets)
        return markets

    def get_all_active_markets(self,
                               categories: list[str],
                               min_liquidity: float = 500) -> list[dict]:
        """Obtiene todos los mercados activos de las categorías seleccionadas."""
        all_markets = []

        for category in categories:
            markets = self.get_markets_by_category(category, limit=50)
            filtered = [
                m for m in markets
                if m.get("liquidity", 0) >= min_liquidity
            ]
            all_markets.extend(filtered)

        # Eliminar duplicados por ID
        seen = set()
        unique = []
        for m in all_markets:
            if m["id"] not in seen:
                seen.add(m["id"])
                unique.append(m)

        return unique

    def get_price_with_history(self, token_id: str) -> Optional[dict]:
        """Obtiene precio actual y lo añade al historial."""
        price_data = self.client.get_market_price(token_id)

        if price_data:
            if token_id not in self._price_history:
                self._price_history[token_id] = []

            self._price_history[token_id].append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "price": price_data["price"],
            })

            # Mantener solo últimas 1000 entradas
            if len(self._price_history[token_id]) > 1000:
                self._price_history[token_id] = (
                    self._price_history[token_id][-1000:]
                )

            price_data["history_length"] = len(
                self._price_history[token_id]
            )

        return price_data

    def get_price_history(self, token_id: str) -> list[dict]:
        """Obtiene el historial de precios de un token."""
        return self._price_history.get(token_id, [])

    def calculate_momentum(self, token_id: str,
                           periods: int = 10) -> Optional[float]:
        """
        Calcula el momentum de precio.
        Retorna cambio porcentual en los últimos N períodos.
        """
        history = self._price_history.get(token_id, [])

        if len(history) < periods + 1:
            return None

        current = history[-1]["price"]
        past = history[-(periods + 1)]["price"]

        if past == 0:
            return None

        return ((current - past) / past) * 100

    def calculate_volatility(self, token_id: str,
                             periods: int = 20) -> Optional[float]:
        """Calcula la volatilidad (desviación estándar de retornos)."""
        history = self._price_history.get(token_id, [])

        if len(history) < periods + 1:
            return None

        prices = [h["price"] for h in history[-(periods + 1):]]
        returns = []

        for i in range(1, len(prices)):
            if prices[i - 1] > 0:
                ret = (prices[i] - prices[i - 1]) / prices[i - 1]
                returns.append(ret)

        if not returns:
            return None

        import numpy as np
        return float(np.std(returns) * 100)

    def _is_cache_valid(self, key: str) -> bool:
        """Verifica si el caché es válido."""
        if key not in self._cache:
            return False
        elapsed = time.time() - self._cache[key]["timestamp"]
        return elapsed < self._cache_ttl

    def _update_cache(self, key: str, data):
        """Actualiza el caché."""
        self._cache[key] = {
            "data": data,
            "timestamp": time.time(),
        }
