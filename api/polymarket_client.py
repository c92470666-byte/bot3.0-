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
