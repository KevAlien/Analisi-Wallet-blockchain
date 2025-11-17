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

# New LONG Entry Strategies
from .long_bullish_divergence_strategy import LongBullishDivergenceStrategy
from .long_ema_bounce_strategy import LongEMABounceStrategy
from .long_support_oi_buildup_strategy import LongSupportOIBuildupStrategy
from .long_pivot_confluence_strategy import LongPivotConfluenceStrategy
from .long_fibonacci_accumulation_strategy import LongFibonacciAccumulationStrategy

# New SHORT Entry Strategies
from .short_bearish_divergence_strategy import ShortBearishDivergenceStrategy
from .short_ema_rejection_strategy import ShortEMARejectionStrategy
from .short_resistance_oi_buildup_strategy import ShortResistanceOIBuildupStrategy
from .short_head_shoulders_strategy import ShortHeadShouldersStrategy
from .short_overextension_reversal_strategy import ShortOverextensionReversalStrategy

# A+ Confluence Checker
from .aplus_confluence_checker import APlusConfluenceChecker, ConfluenceResult

__all__ = [
    # Base classes
    'BaseStrategy',
    'TradingSignal',
    'SignalType',
    'SignalStrength',

    # Original Strategies
    'EMACrossoverStrategy',
    'RSIDivergenceStrategy',
    'ScalpingTripleStrategy',
    'OpenInterestStrategy',
    'OpenInterestData',
    'DivergenceDetectorStrategy',

    # LONG Entry Strategies
    'LongBullishDivergenceStrategy',
    'LongEMABounceStrategy',
    'LongSupportOIBuildupStrategy',
    'LongPivotConfluenceStrategy',
    'LongFibonacciAccumulationStrategy',

    # SHORT Entry Strategies
    'ShortBearishDivergenceStrategy',
    'ShortEMARejectionStrategy',
    'ShortResistanceOIBuildupStrategy',
    'ShortHeadShouldersStrategy',
    'ShortOverextensionReversalStrategy',

    # Confluence Checker
    'APlusConfluenceChecker',
    'ConfluenceResult',
]
