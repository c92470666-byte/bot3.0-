"""
Cliente para la API de Polymarket (CLOB).
Maneja autenticación, consulta de mercados y ejecución de órdenes.
"""

import time
import requests
from typing import Optional
from loguru import logger


class PolymarketClient:
    """
    Cliente principal para interactuar con Polymarket.
    Soporta tanto CLOB API como Gamma Markets API.
    """

    BASE_URL = "https://clob.polymarket.com"
    GAMMA_URL = "https://gamma-api.polymarket.com"

    def __init__(self, api_key: str = "", api_secret: str = "",
                 passphrase: str = ""):
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

        if api_key:
            self._session.headers.update({
                "POLY_API_KEY": api_key,
                "POLY_PASSPHRASE": passphrase,
            })

        self._rate_limit_delay = 0.5  # segundos entre requests

    def is_configured(self) -> bool:
        """Verifica si las credenciales están configuradas."""
        return bool(self.api_key and self.api_secret)

    def test_connection(self) -> dict:
        """Prueba la conexión con la API."""
        try:
            response = self._session.get(
                f"{self.BASE_URL}/time",
                timeout=10
            )
            if response.status_code == 200:
                return {"success": True, "message": "Conexión exitosa"}
            return {
                "success": False,
                "message": f"Error HTTP {response.status_code}"
            }
        except requests.exceptions.ConnectionError:
            return {"success": False, "message": "No se pudo conectar"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def get_markets(self, limit: int = 50, active: bool = True,
                    category: Optional[str] = None) -> list[dict]:
        """
        Obtiene mercados disponibles.
        Usa Gamma API para listado de mercados.
        """
        try:
            params = {
                "limit": limit,
                "active": str(active).lower(),
                "closed": "false",
            }

            if category:
                params["tag"] = category

            response = self._session.get(
                f"{self.GAMMA_URL}/markets",
                params=params,
                timeout=15,
            )
            response.raise_for_status()

            markets = response.json()
            time.sleep(self._rate_limit_delay)

            return self._parse_markets(markets)

        except Exception as e:
            logger.error(f"Error obteniendo mercados: {e}")
            return []

    def get_market_detail(self, market_id: str) -> Optional[dict]:
        """Obtiene detalle de un mercado específico."""
        try:
            response = self._session.get(
                f"{self.GAMMA_URL}/markets/{market_id}",
                timeout=10,
            )
            response.raise_for_status()
            time.sleep(self._rate_limit_delay)
            return response.json()
        except Exception as e:
            logger.error(f"Error obteniendo mercado {market_id}: {e}")
            return None

    def get_market_price(self, token_id: str) -> Optional[dict]:
        """Obtiene el precio actual de un token."""
        try:
            response = self._session.get(
                f"{self.BASE_URL}/price",
                params={"token_id": token_id},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            time.sleep(self._rate_limit_delay)
            return {
                "price": float(data.get("price", 0)),
                "spread": float(data.get("spread", 0)),
            }
        except Exception as e:
            logger.error(f"Error obteniendo precio: {e}")
            return None

    def get_orderbook(self, token_id: str) -> Optional[dict]:
        """Obtiene el libro de órdenes de un token."""
        try:
            response = self._session.get(
                f"{self.BASE_URL}/book",
                params={"token_id": token_id},
                timeout=10,
            )
            response.raise_for_status()
            time.sleep(self._rate_limit_delay)
            return response.json()
        except Exception as e:
            logger.error(f"Error obteniendo orderbook: {e}")
            return None

    def get_midpoint(self, token_id: str) -> Optional[float]:
        """Obtiene el precio medio de un token."""
    def get_midpoint(self, token_id: str) -> Optional[float]:
        """Obtiene el precio medio de un token."""
        try:
            response = self._session.get(
                f"{self.BASE_URL}/midpoint",
                params={"token_id": token_id},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            time.sleep(self._rate_limit_delay)
            return float(data.get("mid", 0))
        except Exception as e:
            logger.error(f"Error obteniendo midpoint: {e}")
            return None

    def place_order(self, token_id: str, side: str, price: float,
                    size: float, order_type: str = "GTC") -> Optional[dict]:
        """
        Coloca una orden en el CLOB.
        SOLO funciona en modo REAL con credenciales válidas.
        """
        if not self.is_configured():
            logger.error("API no configurada. No se puede colocar orden real.")
            return None

        try:
            payload = {
                "tokenID": token_id,
                "side": side.upper(),
                "price": str(price),
                "size": str(size),
                "type": order_type,
            }

            logger.info(
                f"Colocando orden: {side} {size} @ {price} "
                f"(token: {token_id[:20]}...)"
            )

            response = self._session.post(
                f"{self.BASE_URL}/order",
                json=payload,
                timeout=15,
            )
            response.raise_for_status()
            result = response.json()

            logger.info(f"Orden colocada: {result.get('orderID', 'N/A')}")
            time.sleep(self._rate_limit_delay)
            return result

        except requests.exceptions.HTTPError as e:
            logger.error(f"Error HTTP colocando orden: {e}")
            logger.error(f"Response: {e.response.text if e.response else 'N/A'}")
            return None
        except Exception as e:
            logger.error(f"Error colocando orden: {e}")
            return None

    def cancel_order(self, order_id: str) -> bool:
        """Cancela una orden existente."""
        if not self.is_configured():
            return False

        try:
            response = self._session.delete(
                f"{self.BASE_URL}/order/{order_id}",
                timeout=10,
            )
            response.raise_for_status()
            logger.info(f"Orden cancelada: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelando orden {order_id}: {e}")
            return False

    def get_open_orders(self) -> list[dict]:
        """Obtiene órdenes abiertas del usuario."""
        if not self.is_configured():
            return []

        try:
            response = self._session.get(
                f"{self.BASE_URL}/orders",
                params={"state": "LIVE"},
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error obteniendo órdenes abiertas: {e}")
            return []

    def get_positions(self) -> list[dict]:
        """Obtiene posiciones actuales del usuario."""
        if not self.is_configured():
            return []

        try:
            response = self._session.get(
                f"{self.BASE_URL}/positions",
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error obteniendo posiciones: {e}")
            return []

    def _parse_markets(self, raw_markets: list) -> list[dict]:
        """Parsea y normaliza datos de mercados."""
        parsed = []
        for m in raw_markets:
            try:
                tokens = m.get("tokens", [])
                yes_token = None
                no_token = None

                for token in tokens:
                    outcome = token.get("outcome", "").lower()
                    if outcome == "yes":
                        yes_token = token
                    elif outcome == "no":
                        no_token = token

                parsed.append({
                    "id": m.get("id", ""),
                    "condition_id": m.get("condition_id", ""),
                    "question": m.get("question", "Sin título"),
                    "description": m.get("description", ""),
                    "category": m.get("tags", [{}])[0].get("label", "other")
                        if m.get("tags") else "other",
                    "end_date": m.get("end_date_iso", ""),
                    "active": m.get("active", False),
                    "closed": m.get("closed", False),
                    "volume": float(m.get("volume", 0)),
                    "liquidity": float(m.get("liquidity", 0)),
                    "yes_token_id": (
                        yes_token.get("token_id", "") if yes_token else ""
                    ),
                    "no_token_id": (
                        no_token.get("token_id", "") if no_token else ""
                    ),
                    "yes_price": (
                        float(yes_token.get("price", 0.5))
                        if yes_token else 0.5
                    ),
                    "no_price": (
                        float(no_token.get("price", 0.5))
                        if no_token else 0.5
                    ),
                    "image": m.get("image", ""),
                })
            except Exception as e:
                logger.debug(f"Error parseando mercado: {e}")
                continue

        return parsed

    def search_markets(self, query: str, limit: int = 20) -> list[dict]:
        """Busca mercados por texto."""
        try:
            response = self._session.get(
                f"{self.GAMMA_URL}/markets",
                params={
                    "limit": limit,
                    "active": "true",
                    "closed": "false",
                    "q": query,
                },
                timeout=15,
            )
            response.raise_for_status()
            return self._parse_markets(response.json())
        except Exception as e:
            logger.error(f"Error buscando mercados: {e}")
            return []
