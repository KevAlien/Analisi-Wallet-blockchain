"""
Trading strategies for crypto bot.
"""
from .base_strategy import (
    BaseStrategy,
    TradingSignal,
    SignalType,
    SignalStrength
)
from .ema_crossover_strategy import EMACrossoverStrategy
from .rsi_divergence_strategy import RSIDivergenceStrategy
from .scalping_triple_strategy import ScalpingTripleStrategy
from .open_interest_strategy import OpenInterestStrategy, OpenInterestData
from .divergence_detector_strategy import DivergenceDetectorStrategy

__all__ = [
    # Base classes
    'BaseStrategy',
    'TradingSignal',
    'SignalType',
    'SignalStrength',

    # Strategies
    'EMACrossoverStrategy',
    'RSIDivergenceStrategy',
    'ScalpingTripleStrategy',
    'OpenInterestStrategy',
    'OpenInterestData',
    'DivergenceDetectorStrategy',
]
