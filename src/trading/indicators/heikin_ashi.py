"""
Heikin Ashi candlestick transformation.

Formulas:
HA_Close = (Open + High + Low + Close) / 4
HA_Open = (HA_Open(prev) + HA_Close(prev)) / 2
HA_High = Max(High, HA_Open, HA_Close)
HA_Low = Min(Low, HA_Open, HA_Close)
"""
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime
from .base_indicator import Candle


@dataclass
class HeikinAshiCandle:
    """Heikin Ashi transformed candle."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    original_candle: Candle

    @property
    def is_green(self) -> bool:
        """Check if Heikin Ashi candle is green (bullish)."""
        return self.close > self.open

    @property
    def is_red(self) -> bool:
        """Check if Heikin Ashi candle is red (bearish)."""
        return self.close < self.open

    @property
    def body_size(self) -> float:
        """Size of candle body."""
        return abs(self.close - self.open)

    @property
    def has_no_lower_shadow(self) -> bool:
        """Check if candle has no lower shadow (very bullish)."""
        return self.low == min(self.open, self.close)

    @property
    def has_no_upper_shadow(self) -> bool:
        """Check if candle has no upper shadow (very bearish)."""
        return self.high == max(self.open, self.close)

    @property
    def is_strong_bullish(self) -> bool:
        """Strong bullish candle: green with small/no lower shadow."""
        if not self.is_green:
            return False
        lower_shadow = min(self.open, self.close) - self.low
        body = self.body_size
        return body > 0 and lower_shadow / body < 0.2

    @property
    def is_strong_bearish(self) -> bool:
        """Strong bearish candle: red with small/no upper shadow."""
        if not self.is_red:
            return False
        upper_shadow = self.high - max(self.open, self.close)
        body = self.body_size
        return body > 0 and upper_shadow / body < 0.2


class HeikinAshi:
    """Heikin Ashi candlestick transformer."""

    def __init__(self):
        """Initialize Heikin Ashi transformer."""
        self.ha_candles: List[HeikinAshiCandle] = []
        self.previous_ha_open: Optional[float] = None
        self.previous_ha_close: Optional[float] = None

    def transform(self, candles: List[Candle]) -> List[HeikinAshiCandle]:
        """
        Transform regular candles to Heikin Ashi candles.

        Args:
            candles: List of regular Candle objects

        Returns:
            List of HeikinAshiCandle objects
        """
        if not candles:
            return []

        # Process only the new candle if we have history
        if self.ha_candles:
            new_candle = candles[-1]
            ha_candle = self._transform_single(new_candle)
            self.ha_candles.append(ha_candle)
            return self.ha_candles

        # First time: transform all candles
        for candle in candles:
            ha_candle = self._transform_single(candle)
            self.ha_candles.append(ha_candle)

        return self.ha_candles

    def _transform_single(self, candle: Candle) -> HeikinAshiCandle:
        """
        Transform a single candle to Heikin Ashi.

        Args:
            candle: Regular Candle object

        Returns:
            HeikinAshiCandle object
        """
        # Calculate HA Close
        ha_close = (candle.open + candle.high + candle.low + candle.close) / 4

        # Calculate HA Open
        if self.previous_ha_open is None or self.previous_ha_close is None:
            # First candle: use regular open
            ha_open = candle.open
        else:
            ha_open = (self.previous_ha_open + self.previous_ha_close) / 2

        # Calculate HA High and Low
        ha_high = max(candle.high, ha_open, ha_close)
        ha_low = min(candle.low, ha_open, ha_close)

        # Store for next calculation
        self.previous_ha_open = ha_open
        self.previous_ha_close = ha_close

        return HeikinAshiCandle(
            timestamp=candle.timestamp,
            open=ha_open,
            high=ha_high,
            low=ha_low,
            close=ha_close,
            volume=candle.volume,
            original_candle=candle
        )

    def get_latest(self) -> Optional[HeikinAshiCandle]:
        """Get the most recent Heikin Ashi candle."""
        return self.ha_candles[-1] if self.ha_candles else None

    def get_previous(self) -> Optional[HeikinAshiCandle]:
        """Get the previous Heikin Ashi candle."""
        return self.ha_candles[-2] if len(self.ha_candles) >= 2 else None

    def is_uptrend(self, lookback: int = 3) -> bool:
        """
        Check if Heikin Ashi indicates uptrend.

        Args:
            lookback: Number of candles to check

        Returns:
            True if in uptrend (consecutive green candles)
        """
        if len(self.ha_candles) < lookback:
            return False

        recent_candles = self.ha_candles[-lookback:]
        return all(candle.is_green for candle in recent_candles)

    def is_downtrend(self, lookback: int = 3) -> bool:
        """
        Check if Heikin Ashi indicates downtrend.

        Args:
            lookback: Number of candles to check

        Returns:
            True if in downtrend (consecutive red candles)
        """
        if len(self.ha_candles) < lookback:
            return False

        recent_candles = self.ha_candles[-lookback:]
        return all(candle.is_red for candle in recent_candles)

    def trend_changed_to_bullish(self) -> bool:
        """
        Check if trend just changed to bullish.

        Returns:
            True if latest candle is green and previous was red
        """
        latest = self.get_latest()
        previous = self.get_previous()

        if not latest or not previous:
            return False

        return latest.is_green and previous.is_red

    def trend_changed_to_bearish(self) -> bool:
        """
        Check if trend just changed to bearish.

        Returns:
            True if latest candle is red and previous was green
        """
        latest = self.get_latest()
        previous = self.get_previous()

        if not latest or not previous:
            return False

        return latest.is_red and previous.is_green

    def green_candle_exceeds_previous(self) -> bool:
        """
        Check if current green candle exceeds previous green candle.
        (Signal for EMA strategy entry)

        Returns:
            True if current green candle is larger than previous
        """
        latest = self.get_latest()
        previous = self.get_previous()

        if not latest or not previous:
            return False

        if not (latest.is_green and previous.is_green):
            return False

        return latest.close > previous.close and latest.body_size > previous.body_size

    def consecutive_green_candles(self, count: int = 2) -> bool:
        """
        Check for consecutive green candles.

        Args:
            count: Number of consecutive green candles required

        Returns:
            True if there are at least 'count' consecutive green candles
        """
        if len(self.ha_candles) < count:
            return False

        recent = self.ha_candles[-count:]
        return all(candle.is_green for candle in recent)

    def consecutive_red_candles(self, count: int = 2) -> bool:
        """
        Check for consecutive red candles.

        Args:
            count: Number of consecutive red candles required

        Returns:
            True if there are at least 'count' consecutive red candles
        """
        if len(self.ha_candles) < count:
            return False

        recent = self.ha_candles[-count:]
        return all(candle.is_red for candle in recent)

    def get_candles(self, lookback: int = 10) -> List[HeikinAshiCandle]:
        """
        Get recent Heikin Ashi candles.

        Args:
            lookback: Number of candles to retrieve

        Returns:
            List of recent HeikinAshiCandle objects
        """
        return self.ha_candles[-lookback:] if len(self.ha_candles) >= lookback else self.ha_candles.copy()

    def reset(self):
        """Reset Heikin Ashi to initial state."""
        self.ha_candles = []
        self.previous_ha_open = None
        self.previous_ha_close = None
