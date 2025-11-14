"""
Orchestration modules for coordinating trading bot components.
"""
from .signal_aggregator import SignalAggregator, AggregatedSignal, AggregatedSignalType

__all__ = [
    'SignalAggregator',
    'AggregatedSignal',
    'AggregatedSignalType',
]
