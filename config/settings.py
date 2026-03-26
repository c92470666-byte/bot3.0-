"""
Gestión centralizada de configuración.
Toda la configuración se maneja via JSON, nunca editando código.
"""

import json
import os
import copy
from pathlib import Path
from typing import Any, Optional
from loguru import logger
from .validators import ConfigValidator


class ConfigManager:
    """
    Gestor de configuración del bot.
    Lee/escribe configuración desde JSON.
    El usuario NUNCA necesita tocar código.
    """

    CONFIG_FILE = "data/config.json"
    DEFAULTS_FILE = "config/defaults.json"

    def __init__(self):
        self._config: dict = {}
        self._callbacks: list = []
        self._validator = ConfigValidator()

    def load(self) -> dict:
        """Carga la configuración. Si no existe, crea desde defaults."""
        defaults = self._load_defaults()

        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, "r") as f:
                    user_config = json.load(f)
                # Merge: defaults + user config (user gana)
                self._config = self._deep_merge(defaults, user_config)
                logger.info("Configuración del usuario cargada")
            except json.JSONDecodeError:
                logger.warning("Config corrupta, usando defaults")
                self._config = defaults
        else:
            self._config = defaults
            self.save()
            logger.info("Primera ejecución: configuración por defecto creada")

        return self._config

    def save(self) -> bool:
        """Guarda la configuración actual a disco."""
        try:
            os.makedirs(os.path.dirname(self.CONFIG_FILE), exist_ok=True)

            # No guardar secrets en texto plano si hay encriptación
            config_to_save = copy.deepcopy(self._config)

            with open(self.CONFIG_FILE, "w") as f:
                json.dump(config_to_save, f, indent=2, ensure_ascii=False)

            logger.info("Configuración guardada correctamente")
            self._notify_callbacks()
            return True
        except Exception as e:
            logger.error(f"Error guardando configuración: {e}")
            return False

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Obtiene un valor usando dot notation.
        Ejemplo: config.get("risk.stop_loss_pct")
        """
        keys = key_path.split(".")
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def set(self, key_path: str, value: Any) -> bool:
        """
        Establece un valor usando dot notation.
        Ejemplo: config.set("risk.stop_loss_pct", 10.0)
        """
        keys = key_path.split(".")
        config = self._config

        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        config[keys[-1]] = value
        return self.save()

    def update(self, updates: dict) -> tuple[bool, list[str]]:
        """
        Actualiza múltiples valores desde el formulario web.
        Retorna (éxito, lista_de_errores).
        """
        errors = self._validator.validate(updates)
        if errors:
            return False, errors

        self._config = self._deep_merge(self._config, updates)
        success = self.save()
        return success, []

    def get_all(self) -> dict:
        """Retorna toda la configuración (copia segura)."""
        config = copy.deepcopy(self._config)
        # Ocultar secrets parcialmente para el dashboard
        if config.get("api", {}).get("secret"):
            secret = config["api"]["secret"]
            config["api"]["secret_masked"] = (
                secret[:4] + "****" + secret[-4:] if len(secret) > 8 else "****"
            )
        return config

    def reset_to_defaults(self) -> bool:
        """Resetea toda la configuración a valores por defecto."""
        self._config = self._load_defaults()
        return self.save()

    def on_change(self, callback):
        """Registra un callback para cuando cambie la configuración."""
        self._callbacks.append(callback)

    def _notify_callbacks(self):
        """Notifica a todos los listeners de cambios."""
        for cb in self._callbacks:
            try:
                cb(self._config)
            except Exception as e:
                logger.error(f"Error en callback de configuración: {
