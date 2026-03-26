"""Estrategias de trading."""
from .base import BaseStrategy
from .momentum import MomentumStrategy
from .mean_reversion import MeanReversionStrategy
from .sentiment import SentimentStrategy
from .arbitrage import ArbitrageStrategy

STRATEGIES = {
    "momentum": MomentumStrategy,
    "mean_reversion": MeanReversionStrategy,
    "sentiment": SentimentStrategy,
    "arbitrage": ArbitrageStrategy,
}

def get_strategy(name: str, config: dict) -> BaseStrategy:
    """Factory para obtener una estrategia por nombre."""
    strategy_class = STRATEGIES.get(name)
    if not strategy_class:
        raise ValueError(f"Estrategia desconocida: {name}")
    return strategy_class(config)
