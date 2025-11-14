"""
Exponential Moving Average (EMA) indicator.

Formula:
EMA(today) = (Price(today) × Multiplier) + (EMA(yesterday) × (1 - Multiplier))
Multiplier = 2 / (Period + 1)
"""
from typing import List, Optional
from .base_indicator import BaseIndicator, Candle


class EMA(BaseIndicator):
    """Exponential Moving Average indicator."""

    def __init__(self, period: int = 20):
        """
        Initialize EMA indicator.

        Args:
            period: The lookback period for EMA calculation
        """
        super().__init__(period)
        self.multiplier = 2 / (period + 1)
        self.ema_value: Optional[float] = None

    def calculate(self, candles: List[Candle]) -> Optional[float]:
        """
        Calculate EMA value.

        Args:
            candles: List of Candle objects

        Returns:
            Current EMA value or None if insufficient data
        """
        if len(candles) < self.period:
            return None

        # If first calculation, use SMA as initial EMA
        if self.ema_value is None:
            prices = [c.close for c in candles[-self.period:]]
            self.ema_value = sum(prices) / len(prices)
            return self.ema_value

        # Calculate EMA using the formula
        current_price = candles[-1].close
        self.ema_value = (current_price * self.multiplier) + (self.ema_value * (1 - self.multiplier))

        return self.ema_value

    def cross_above(self, other_ema: 'EMA') -> bool:
        """
        Check if this EMA crossed above another EMA.

        Args:
            other_ema: Another EMA indicator to compare

        Returns:
            True if this EMA crossed above the other EMA
        """
        if not self.is_ready() or not other_ema.is_ready():
            return False

        # Current: fast above slow
        # Previous: fast below or equal slow
        current_above = self.current_value > other_ema.current_value
        previous_below_or_equal = self.previous_value <= other_ema.previous_value

        return current_above and previous_below_or_equal

    def cross_below(self, other_ema: 'EMA') -> bool:
        """
        Check if this EMA crossed below another EMA.

        Args:
            other_ema: Another EMA indicator to compare

        Returns:
            True if this EMA crossed below the other EMA
        """
        if not self.is_ready() or not other_ema.is_ready():
            return False

        # Current: fast below slow
        # Previous: fast above or equal slow
        current_below = self.current_value < other_ema.current_value
        previous_above_or_equal = self.previous_value >= other_ema.previous_value

        return current_below and previous_above_or_equal

    def reset(self):
        """Reset EMA to initial state."""
        super().reset()
        self.ema_value = None


class MultiEMA:
    """Manages multiple EMAs for crossover strategies."""

    def __init__(self, periods: List[int]):
        """
        Initialize multiple EMAs.

        Args:
            periods: List of EMA periods (e.g., [8, 14, 50, 200])
        """
        self.periods = sorted(periods)
        self.emas = {period: EMA(period) for period in periods}

    def update(self, candles: List[Candle]) -> dict:
        """
        Update all EMAs.

        Args:
            candles: List of Candle objects

        Returns:
            Dictionary mapping period to current EMA value
        """
        return {
            period: ema.update(candles)
            for period, ema in self.emas.items()
        }

    def get_ema(self, period: int) -> Optional[EMA]:
        """Get EMA for a specific period."""
        return self.emas.get(period)

    def all_ready(self) -> bool:
        """Check if all EMAs are ready."""
        return all(ema.is_ready() for ema in self.emas.values())

    def is_bullish_alignment(self) -> bool:
        """
        Check if EMAs are in bullish alignment (fast > medium > slow).

        Returns:
            True if EMAs are in bullish order
        """
        if not self.all_ready():
            return False

        values = [ema.current_value for ema in self.emas.values()]
        # Check if values are in descending order (fast EMAs > slow EMAs)
        return all(values[i] > values[i + 1] for i in range(len(values) - 1))

    def is_bearish_alignment(self) -> bool:
        """
        Check if EMAs are in bearish alignment (fast < medium < slow).

        Returns:
            True if EMAs are in bearish order
        """
        if not self.all_ready():
            return False

        values = [ema.current_value for ema in self.emas.values()]
        # Check if values are in ascending order (fast EMAs < slow EMAs)
        return all(values[i] < values[i + 1] for i in range(len(values) - 1))

    def get_support_resistance(self) -> dict:
        """
        Get potential support/resistance levels from EMAs.

        Returns:
            Dictionary with support and resistance EMA values
        """
        return {
            'support': [ema.current_value for ema in self.emas.values() if ema.current_value],
            'resistance': [ema.current_value for ema in self.emas.values() if ema.current_value]
        }
