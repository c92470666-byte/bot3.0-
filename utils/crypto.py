"""
Encriptación de credenciales sensibles.
"""

import os
import base64
from cryptography.fernet import Fernet
from loguru import logger


class CredentialEncryptor:
    """Encripta/desencripta credenciales de API."""

    KEY_FILE = "data/.encryption_key"

    def __init__(self):
        self._fernet = Fernet(self._get_or_create_key())

    def encrypt(self, plaintext: str) -> str:
        """Encripta un texto."""
        if not plaintext:
            return ""
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Desencripta un texto."""
        if not ciphertext:
            return ""
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except Exception:
            logger.warning("No se pudo desencriptar, retornando original")
            return ciphertext

    def _get_or_create_key(self) -> bytes:
        """Obtiene o crea la clave de encriptación."""
        # Primero intentar variable de entorno
        env_key = os.environ.get("POLYBOT_ENCRYPTION_KEY")
        if env_key:
            return env_key.encode()

        # Si no, usar archivo local
        os.makedirs(os.path.dirname(self.KEY_FILE), exist_ok=True)

        if os.path.exists(self.KEY_FILE):
            with open(self.KEY_FILE, "rb") as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(self.KEY_FILE, "wb") as f:
                f.write(key)
            # Restringir permisos
            os.chmod(self.KEY_FILE, 0o600)
            logger.info("Clave de encriptación generada")
            return key
