"""
Fibonacci Retracement Indicator.

Calculates Fibonacci retracement levels from the last significant price impulse.
"""
from typing import List, Optional, Dict
from .base_indicator import BaseIndicator, Candle


class FibonacciRetracement(BaseIndicator):
    """
    Fibonacci Retracement calculator.

    Identifies Fibonacci retracement levels (0.236, 0.382, 0.5, 0.618, 0.786)
    from the last significant impulse move.
    """

    # Standard Fibonacci levels
    LEVELS = {
        '0.0': 0.0,
        '0.236': 0.236,
        '0.382': 0.382,
        '0.5': 0.5,
        '0.618': 0.618,
        '0.786': 0.786,
        '1.0': 1.0
    }

    def __init__(self, lookback: int = 50):
        """
        Initialize Fibonacci Retracement.

        Args:
            lookback: Number of candles to look back for swing high/low
        """
        super().__init__(period=lookback)
        self.lookback = lookback
        self.swing_high: Optional[float] = None
        self.swing_low: Optional[float] = None
        self.trend_direction: Optional[str] = None  # 'up' or 'down'
        self.levels_cache: Dict[str, float] = {}

    def calculate(self, candles: List[Candle]) -> Optional[float]:
        """
        Calculate Fibonacci levels from recent swing points.

        Args:
            candles: List of Candle objects

        Returns:
            Current 0.618 level (most important for entries)
        """
        if len(candles) < self.lookback:
            return None

        recent_candles = candles[-self.lookback:]

        # Find swing high and low
        self.swing_high = max(c.high for c in recent_candles)
        self.swing_low = min(c.low for c in recent_candles)

        # Determine trend direction based on most recent price action
        current_price = candles[-1].close
        mid_point = (self.swing_high + self.swing_low) / 2

        if current_price > mid_point:
            self.trend_direction = 'up'
            # For uptrend, calculate retracements from high to low
            self._calculate_levels(self.swing_high, self.swing_low, 'down')
        else:
            self.trend_direction = 'down'
            # For downtrend, calculate extensions from low to high
            self._calculate_levels(self.swing_low, self.swing_high, 'up')

        # Return the golden ratio level (0.618) as the primary value
        return self.levels_cache.get('0.618')

    def _calculate_levels(self, start: float, end: float, direction: str):
        """
        Calculate all Fibonacci levels.

        Args:
            start: Starting price (swing high for retracements)
            end: Ending price (swing low for retracements)
            direction: 'up' or 'down' for level calculation
        """
        diff = abs(start - end)

        self.levels_cache = {}

        for name, ratio in self.LEVELS.items():
            if direction == 'down':
                # Retracement from high to low
                level = start - (diff * ratio)
            else:
                # Extension from low to high
                level = start + (diff * ratio)

            self.levels_cache[name] = level

    def get_levels(self) -> Dict[str, float]:
        """
        Get all calculated Fibonacci levels.

        Returns:
            Dictionary of level names to price values
        """
        return self.levels_cache.copy()

    def is_at_level(self, price: float, level_name: str = '0.618', tolerance: float = 0.005) -> bool:
        """
        Check if price is near a specific Fibonacci level.

        Args:
            price: Current price to check
            level_name: Name of Fibonacci level (e.g., '0.618')
            tolerance: Percentage tolerance (0.005 = 0.5%)

        Returns:
            True if price is within tolerance of the level
        """
        if level_name not in self.levels_cache:
            return False

        level_price = self.levels_cache[level_name]
        threshold = level_price * tolerance

        return abs(price - level_price) <= threshold

    def is_in_golden_zone(self, price: float, tolerance: float = 0.01) -> bool:
        """
        Check if price is in the golden zone (0.618-0.786 retracement).

        This is a high-probability reversal zone.

        Args:
            price: Current price
            tolerance: Additional tolerance percentage

        Returns:
            True if price is in the golden zone
        """
        if '0.618' not in self.levels_cache or '0.786' not in self.levels_cache:
            return False

        level_618 = self.levels_cache['0.618']
        level_786 = self.levels_cache['0.786']

        lower = min(level_618, level_786)
        upper = max(level_618, level_786)

        # Add tolerance
        range_size = upper - lower
        lower -= range_size * tolerance
        upper += range_size * tolerance

        return lower <= price <= upper

    def get_nearest_level(self, price: float) -> tuple[str, float]:
        """
        Find the nearest Fibonacci level to current price.

        Args:
            price: Current price

        Returns:
            Tuple of (level_name, level_price)
        """
        if not self.levels_cache:
            return ('', 0.0)

        nearest_level = min(
            self.levels_cache.items(),
            key=lambda x: abs(x[1] - price)
        )

        return nearest_level

    def get_retracement_depth(self, current_price: float) -> Optional[float]:
        """
        Calculate how deep the current retracement is as a percentage.

        Args:
            current_price: Current price

        Returns:
            Retracement percentage (0.0 to 1.0+)
        """
        if self.swing_high is None or self.swing_low is None:
            return None

        impulse_range = abs(self.swing_high - self.swing_low)
        if impulse_range == 0:
            return 0.0

        if self.trend_direction == 'up':
            # Measure retracement from swing high
            retracement = self.swing_high - current_price
        else:
            # Measure retracement from swing low
            retracement = current_price - self.swing_low

        return abs(retracement / impulse_range)
