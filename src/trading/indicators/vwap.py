"""
Volume Weighted Average Price (VWAP) indicator.

Formula:
VWAP = Σ(Typical Price × Volume) / Σ(Volume)
Typical Price = (High + Low + Close) / 3
"""
from typing import List, Optional
from datetime import datetime, time
from .base_indicator import BaseIndicator, Candle


class VWAP(BaseIndicator):
    """Volume Weighted Average Price indicator."""

    def __init__(self, period: Optional[int] = None, reset_daily: bool = True):
        """
        Initialize VWAP indicator.

        Args:
            period: Optional lookback period. If None, uses all data since last reset
            reset_daily: If True, VWAP resets at the start of each day
        """
        super().__init__(period if period else 1)
        self.reset_daily = reset_daily
        self.cumulative_tpv: float = 0.0  # Typical Price × Volume
        self.cumulative_volume: float = 0.0
        self.last_reset_date: Optional[datetime] = None
        self.vwap_value: Optional[float] = None

    def calculate(self, candles: List[Candle]) -> Optional[float]:
        """
        Calculate VWAP value.

        Args:
            candles: List of Candle objects

        Returns:
            Current VWAP value or None if insufficient data
        """
        if not candles:
            return None

        current_candle = candles[-1]

        # Check if we need to reset (new day)
        if self.reset_daily and self._should_reset(current_candle.timestamp):
            self._reset_calculation()

        # Calculate typical price and add to cumulative values
        typical_price = current_candle.typical_price
        volume = current_candle.volume

        self.cumulative_tpv += typical_price * volume
        self.cumulative_volume += volume

        # Avoid division by zero
        if self.cumulative_volume == 0:
            return None

        self.vwap_value = self.cumulative_tpv / self.cumulative_volume

        return self.vwap_value

    def _should_reset(self, current_time: datetime) -> bool:
        """
        Check if VWAP should be reset based on the date.

        Args:
            current_time: Current timestamp

        Returns:
            True if VWAP should reset
        """
        if self.last_reset_date is None:
            self.last_reset_date = current_time.date()
            return False

        current_date = current_time.date()
        if current_date > self.last_reset_date:
            self.last_reset_date = current_date
            return True

        return False

    def _reset_calculation(self):
        """Reset cumulative calculations for new period."""
        self.cumulative_tpv = 0.0
        self.cumulative_volume = 0.0

    def is_above_vwap(self, price: float) -> bool:
        """
        Check if price is above VWAP (bullish signal).

        Args:
            price: Current price to compare

        Returns:
            True if price is above VWAP
        """
        return self.vwap_value is not None and price > self.vwap_value

    def is_below_vwap(self, price: float) -> bool:
        """
        Check if price is below VWAP (bearish signal).

        Args:
            price: Current price to compare

        Returns:
            True if price is below VWAP
        """
        return self.vwap_value is not None and price < self.vwap_value

    def price_crossed_above(self, candles: List[Candle]) -> bool:
        """
        Check if price crossed above VWAP.

        Args:
            candles: Recent candles including current

        Returns:
            True if price crossed above VWAP
        """
        if len(candles) < 2 or len(self.values) < 2:
            return False

        previous_price = candles[-2].close
        current_price = candles[-1].close
        previous_vwap = self.values[-2]
        current_vwap = self.current_value

        if previous_vwap is None or current_vwap is None:
            return False

        # Previous: below, Current: above
        return previous_price <= previous_vwap and current_price > current_vwap

    def price_crossed_below(self, candles: List[Candle]) -> bool:
        """
        Check if price crossed below VWAP.

        Args:
            candles: Recent candles including current

        Returns:
            True if price crossed below VWAP
        """
        if len(candles) < 2 or len(self.values) < 2:
            return False

        previous_price = candles[-2].close
        current_price = candles[-1].close
        previous_vwap = self.values[-2]
        current_vwap = self.current_value

        if previous_vwap is None or current_vwap is None:
            return False

        # Previous: above, Current: below
        return previous_price >= previous_vwap and current_price < current_vwap

    def get_distance_from_vwap(self, price: float) -> Optional[float]:
        """
        Get percentage distance from VWAP.

        Args:
            price: Current price

        Returns:
            Percentage distance from VWAP (positive if above, negative if below)
        """
        if self.vwap_value is None or self.vwap_value == 0:
            return None

        return ((price - self.vwap_value) / self.vwap_value) * 100

    def is_support_established(self, candles: List[Candle], touches: int = 2) -> bool:
        """
        Check if VWAP has been established as support.

        Args:
            candles: Recent candles
            touches: Number of times price should touch VWAP to establish support

        Returns:
            True if VWAP is established as support
        """
        if len(candles) < touches or len(self.values) < touches:
            return False

        touch_count = 0
        tolerance = 0.001  # 0.1% tolerance for "touch"

        for i in range(-touches, 0):
            candle = candles[i]
            vwap = self.values[i]

            if vwap is None:
                continue

            # Check if candle touched VWAP (low near VWAP, but closed above)
            low_near_vwap = abs(candle.low - vwap) / vwap < tolerance
            closed_above = candle.close > vwap

            if low_near_vwap and closed_above:
                touch_count += 1

        return touch_count >= touches

    def is_resistance_established(self, candles: List[Candle], touches: int = 2) -> bool:
        """
        Check if VWAP has been established as resistance.

        Args:
            candles: Recent candles
            touches: Number of times price should touch VWAP to establish resistance

        Returns:
            True if VWAP is established as resistance
        """
        if len(candles) < touches or len(self.values) < touches:
            return False

        touch_count = 0
        tolerance = 0.001  # 0.1% tolerance for "touch"

        for i in range(-touches, 0):
            candle = candles[i]
            vwap = self.values[i]

            if vwap is None:
                continue

            # Check if candle touched VWAP (high near VWAP, but closed below)
            high_near_vwap = abs(candle.high - vwap) / vwap < tolerance
            closed_below = candle.close < vwap

            if high_near_vwap and closed_below:
                touch_count += 1

        return touch_count >= touches

    def reset(self):
        """Reset VWAP to initial state."""
        super().reset()
        self._reset_calculation()
        self.last_reset_date = None
        self.vwap_value = None
