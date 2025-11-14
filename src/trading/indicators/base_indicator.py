"""
Base class for technical indicators.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Candle:
    """Represents a single candlestick with OHLCV data."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    @property
    def typical_price(self) -> float:
        """Calculate typical price: (High + Low + Close) / 3"""
        return (self.high + self.low + self.close) / 3

    @property
    def is_bullish(self) -> bool:
        """Check if candle is bullish (close > open)"""
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        """Check if candle is bearish (close < open)"""
        return self.close < self.open

    @property
    def body_size(self) -> float:
        """Size of candle body"""
        return abs(self.close - self.open)

    @property
    def range(self) -> float:
        """Total range of candle (high - low)"""
        return self.high - self.low


class BaseIndicator(ABC):
    """Base class for all technical indicators."""

    def __init__(self, period: int = 14):
        """
        Initialize indicator.

        Args:
            period: The lookback period for the indicator
        """
        self.period = period
        self.values: List[float] = []
        self.initialized = False

    @abstractmethod
    def calculate(self, candles: List[Candle]) -> Optional[float]:
        """
        Calculate indicator value based on candle data.

        Args:
            candles: List of Candle objects

        Returns:
            Calculated indicator value or None if insufficient data
        """
        pass

    def update(self, candles: List[Candle]) -> Optional[float]:
        """
        Update indicator with new candle data.

        Args:
            candles: List of Candle objects

        Returns:
            Latest indicator value
        """
        value = self.calculate(candles)
        if value is not None:
            self.values.append(value)
            if not self.initialized and len(self.values) >= self.period:
                self.initialized = True
        return value

    @property
    def current_value(self) -> Optional[float]:
        """Get the most recent indicator value."""
        return self.values[-1] if self.values else None

    @property
    def previous_value(self) -> Optional[float]:
        """Get the previous indicator value."""
        return self.values[-2] if len(self.values) >= 2 else None

    def is_ready(self) -> bool:
        """Check if indicator has enough data to be reliable."""
        return self.initialized

    def reset(self):
        """Reset indicator to initial state."""
        self.values = []
        self.initialized = False

    def get_history(self, n: int = 10) -> List[float]:
        """
        Get last n indicator values.

        Args:
            n: Number of historical values to retrieve

        Returns:
            List of last n values
        """
        return self.values[-n:] if len(self.values) >= n else self.values.copy()
