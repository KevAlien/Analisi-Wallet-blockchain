"""
Pivot Points indicator.

Standard Pivot Point formulas:
PP = (High + Low + Close) / 3
R1 = (2 × PP) - Low
S1 = (2 × PP) - High
R2 = PP + (High - Low)
S2 = PP - (High - Low)
R3 = High + 2 × (PP - Low)
S3 = Low - 2 × (High - PP)
"""
from typing import List, Optional, Dict
from dataclasses import dataclass
from datetime import datetime
from .base_indicator import BaseIndicator, Candle


@dataclass
class PivotLevels:
    """Pivot point levels."""
    pp: float  # Pivot Point
    r1: float  # Resistance 1
    r2: float  # Resistance 2
    r3: float  # Resistance 3
    s1: float  # Support 1
    s2: float  # Support 2
    s3: float  # Support 3
    timestamp: datetime

    def get_nearest_support(self, price: float) -> Optional[float]:
        """Get the nearest support level below current price."""
        supports = [self.s1, self.s2, self.s3, self.pp]
        valid_supports = [s for s in supports if s < price]
        return max(valid_supports) if valid_supports else None

    def get_nearest_resistance(self, price: float) -> Optional[float]:
        """Get the nearest resistance level above current price."""
        resistances = [self.r1, self.r2, self.r3, self.pp]
        valid_resistances = [r for r in resistances if r > price]
        return min(valid_resistances) if valid_resistances else None

    def is_at_support(self, price: float, tolerance: float = 0.002) -> bool:
        """
        Check if price is at a support level.

        Args:
            price: Current price
            tolerance: Percentage tolerance (default: 0.2%)

        Returns:
            True if price is near a support level
        """
        supports = [self.s1, self.s2, self.s3]
        for support in supports:
            if abs(price - support) / support < tolerance:
                return True
        return False

    def is_at_resistance(self, price: float, tolerance: float = 0.002) -> bool:
        """
        Check if price is at a resistance level.

        Args:
            price: Current price
            tolerance: Percentage tolerance (default: 0.2%)

        Returns:
            True if price is near a resistance level
        """
        resistances = [self.r1, self.r2, self.r3]
        for resistance in resistances:
            if abs(price - resistance) / resistance < tolerance:
                return True
        return False

    def is_above_pivot(self, price: float) -> bool:
        """Check if price is above pivot point (bullish)."""
        return price > self.pp

    def is_below_pivot(self, price: float) -> bool:
        """Check if price is below pivot point (bearish)."""
        return price < self.pp


class PivotPoints(BaseIndicator):
    """Pivot Points indicator."""

    def __init__(self, reset_daily: bool = True):
        """
        Initialize Pivot Points indicator.

        Args:
            reset_daily: If True, calculate new pivots at start of each day
        """
        super().__init__(period=1)
        self.reset_daily = reset_daily
        self.current_levels: Optional[PivotLevels] = None
        self.last_calculation_date: Optional[datetime] = None
        self.previous_day_high: Optional[float] = None
        self.previous_day_low: Optional[float] = None
        self.previous_day_close: Optional[float] = None

    def calculate(self, candles: List[Candle]) -> Optional[float]:
        """
        Calculate Pivot Points.

        Args:
            candles: List of Candle objects

        Returns:
            Current pivot point value
        """
        if not candles:
            return None

        current_candle = candles[-1]

        # Check if we need to calculate new pivots (new day)
        if self._should_recalculate(current_candle.timestamp):
            # Get previous day's data
            previous_day_data = self._get_previous_day_data(candles)

            if previous_day_data:
                high, low, close = previous_day_data
                self.current_levels = self._calculate_levels(
                    high, low, close, current_candle.timestamp
                )
                self.last_calculation_date = current_candle.timestamp.date()

        return self.current_levels.pp if self.current_levels else None

    def _should_recalculate(self, current_time: datetime) -> bool:
        """
        Check if pivots should be recalculated.

        Args:
            current_time: Current timestamp

        Returns:
            True if pivots should be recalculated
        """
        if not self.reset_daily:
            return self.current_levels is None

        if self.last_calculation_date is None:
            return True

        current_date = current_time.date()
        return current_date > self.last_calculation_date

    def _get_previous_day_data(self, candles: List[Candle]) -> Optional[tuple]:
        """
        Get previous day's high, low, and close.

        Args:
            candles: List of Candle objects

        Returns:
            Tuple of (high, low, close) or None if insufficient data
        """
        if len(candles) < 2:
            return None

        # For simplicity, use the last complete candle as "previous day"
        # In production, you'd filter by actual date boundaries
        prev_candle = candles[-2]
        return (prev_candle.high, prev_candle.low, prev_candle.close)

    def _calculate_levels(self, high: float, low: float, close: float,
                         timestamp: datetime) -> PivotLevels:
        """
        Calculate all pivot levels.

        Args:
            high: Previous period high
            low: Previous period low
            close: Previous period close
            timestamp: Current timestamp

        Returns:
            PivotLevels object with all calculated levels
        """
        # Pivot Point
        pp = (high + low + close) / 3

        # First level support and resistance
        r1 = (2 * pp) - low
        s1 = (2 * pp) - high

        # Second level support and resistance
        r2 = pp + (high - low)
        s2 = pp - (high - low)

        # Third level support and resistance
        r3 = high + 2 * (pp - low)
        s3 = low - 2 * (high - pp)

        return PivotLevels(
            pp=pp, r1=r1, r2=r2, r3=r3,
            s1=s1, s2=s2, s3=s3,
            timestamp=timestamp
        )

    def get_levels(self) -> Optional[PivotLevels]:
        """Get current pivot levels."""
        return self.current_levels

    def support_broken(self, candles: List[Candle]) -> bool:
        """
        Check if a support level was broken.

        Args:
            candles: Recent candles

        Returns:
            True if support was broken (bearish signal)
        """
        if not self.current_levels or len(candles) < 2:
            return False

        current_candle = candles[-1]
        previous_candle = candles[-2]

        supports = [self.current_levels.s1, self.current_levels.s2, self.current_levels.s3]

        for support in supports:
            # Previous candle above support, current candle broke below
            if previous_candle.low > support and current_candle.close < support:
                return True

        return False

    def resistance_broken(self, candles: List[Candle]) -> bool:
        """
        Check if a resistance level was broken.

        Args:
            candles: Recent candles

        Returns:
            True if resistance was broken (bullish signal)
        """
        if not self.current_levels or len(candles) < 2:
            return False

        current_candle = candles[-1]
        previous_candle = candles[-2]

        resistances = [self.current_levels.r1, self.current_levels.r2, self.current_levels.r3]

        for resistance in resistances:
            # Previous candle below resistance, current candle broke above
            if previous_candle.high < resistance and current_candle.close > resistance:
                return True

        return False

    def get_support_resistance_map(self) -> Dict[str, float]:
        """
        Get all support and resistance levels as a dictionary.

        Returns:
            Dictionary of level names to values
        """
        if not self.current_levels:
            return {}

        return {
            'R3': self.current_levels.r3,
            'R2': self.current_levels.r2,
            'R1': self.current_levels.r1,
            'PP': self.current_levels.pp,
            'S1': self.current_levels.s1,
            'S2': self.current_levels.s2,
            'S3': self.current_levels.s3,
        }

    def reset(self):
        """Reset Pivot Points to initial state."""
        super().reset()
        self.current_levels = None
        self.last_calculation_date = None
        self.previous_day_high = None
        self.previous_day_low = None
        self.previous_day_close = None
