"""
Sistema de logging centralizado.
"""

import sys
from loguru import logger as _logger


def setup_logger(level: str = "INFO"):
    """Configura el logger global."""
    _logger.remove()

    # Consola con colores
    _logger.add(
        sys.stdout,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{module}</cyan>:<cyan>{function}</cyan> - "
            "<level>{message}</level>"
        ),
        level=level,
        colorize=True,
    )

    # Archivo rotativo
    _logger.add(
        "logs/polybot_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level="DEBUG",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
            "{module}:{function}:{line} - {message}"
        ),
    )

    # Archivo solo errores
    _logger.add(
        "logs/errors_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="60 days",
        level="ERROR",
    )

    return _logger


logger = _logger
