"""
Swing Points detector for identifying higher highs, higher lows, lower highs, and lower lows.

This indicator is crucial for:
- Identifying trend direction
- Finding optimal entry points for short/long positions
- Detecting trend reversals
"""
from typing import List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from .base_indicator import BaseIndicator, Candle


@dataclass
class SwingPoint:
    """Represents a swing high or swing low point."""
    price: float
    timestamp: datetime
    candle_index: int
    is_high: bool  # True for swing high, False for swing low


class SwingPointDetector(BaseIndicator):
    """
    Detects swing points (highs and lows) in price action.

    A swing high is a peak where the high is higher than N candles on both sides.
    A swing low is a trough where the low is lower than N candles on both sides.
    """

    def __init__(self, lookback: int = 5):
        """
        Initialize Swing Point Detector.

        Args:
            lookback: Number of candles on each side to confirm a swing point
        """
        super().__init__(period=lookback * 2 + 1)
        self.lookback = lookback
        self.swing_highs: List[SwingPoint] = []
        self.swing_lows: List[SwingPoint] = []

    def calculate(self, candles: List[Candle]) -> Optional[float]:
        """
        Calculate and detect swing points.

        Args:
            candles: List of Candle objects

        Returns:
            None (this indicator updates internal state)
        """
        if len(candles) < self.period:
            return None

        # Check for new swing points
        # We look at the candle at position -(lookback + 1) to ensure we have enough candles on both sides
        check_index = len(candles) - self.lookback - 1

        if check_index < self.lookback:
            return None

        check_candle = candles[check_index]

        # Check for swing high
        if self._is_swing_high(candles, check_index):
            swing_high = SwingPoint(
                price=check_candle.high,
                timestamp=check_candle.timestamp,
                candle_index=check_index,
                is_high=True
            )
            # Only add if not already recorded
            if not self.swing_highs or self.swing_highs[-1].timestamp != swing_high.timestamp:
                self.swing_highs.append(swing_high)

        # Check for swing low
        if self._is_swing_low(candles, check_index):
            swing_low = SwingPoint(
                price=check_candle.low,
                timestamp=check_candle.timestamp,
                candle_index=check_index,
                is_high=False
            )
            # Only add if not already recorded
            if not self.swing_lows or self.swing_lows[-1].timestamp != swing_low.timestamp:
                self.swing_lows.append(swing_low)

        return None

    def _is_swing_high(self, candles: List[Candle], index: int) -> bool:
        """
        Check if candle at index is a swing high.

        Args:
            candles: List of candles
            index: Index to check

        Returns:
            True if it's a swing high
        """
        if index < self.lookback or index >= len(candles) - self.lookback:
            return False

        check_high = candles[index].high

        # Check left side
        for i in range(index - self.lookback, index):
            if candles[i].high >= check_high:
                return False

        # Check right side
        for i in range(index + 1, index + self.lookback + 1):
            if candles[i].high >= check_high:
                return False

        return True

    def _is_swing_low(self, candles: List[Candle], index: int) -> bool:
        """
        Check if candle at index is a swing low.

        Args:
            candles: List of candles
            index: Index to check

        Returns:
            True if it's a swing low
        """
        if index < self.lookback or index >= len(candles) - self.lookback:
            return False

        check_low = candles[index].low

        # Check left side
        for i in range(index - self.lookback, index):
            if candles[i].low <= check_low:
                return False

        # Check right side
        for i in range(index + 1, index + self.lookback + 1):
            if candles[i].low <= check_low:
                return False

        return True

    def get_last_swing_high(self) -> Optional[SwingPoint]:
        """Get the most recent swing high."""
        return self.swing_highs[-1] if self.swing_highs else None

    def get_last_swing_low(self) -> Optional[SwingPoint]:
        """Get the most recent swing low."""
        return self.swing_lows[-1] if self.swing_lows else None

    def is_higher_high(self) -> bool:
        """
        Check if the last swing high is higher than the previous one (bullish).

        Returns:
            True if we have a higher high
        """
        if len(self.swing_highs) < 2:
            return False
        return self.swing_highs[-1].price > self.swing_highs[-2].price

    def is_lower_high(self) -> bool:
        """
        Check if the last swing high is lower than the previous one (bearish).

        Returns:
            True if we have a lower high
        """
        if len(self.swing_highs) < 2:
            return False
        return self.swing_highs[-1].price < self.swing_highs[-2].price

    def is_higher_low(self) -> bool:
        """
        Check if the last swing low is higher than the previous one (bullish).

        Returns:
            True if we have a higher low
        """
        if len(self.swing_lows) < 2:
            return False
        return self.swing_lows[-1].price > self.swing_lows[-2].price

    def is_lower_low(self) -> bool:
        """
        Check if the last swing low is lower than the previous one (bearish).

        Returns:
            True if we have a lower low
        """
        if len(self.swing_lows) < 2:
            return False
        return self.swing_lows[-1].price < self.swing_lows[-2].price

    def is_uptrend(self) -> bool:
        """
        Determine if we're in an uptrend (higher highs and higher lows).

        Returns:
            True if uptrend detected
        """
        return self.is_higher_high() and self.is_higher_low()

    def is_downtrend(self) -> bool:
        """
        Determine if we're in a downtrend (lower highs and lower lows).

        Returns:
            True if downtrend detected
        """
        return self.is_lower_high() and self.is_lower_low()

    def is_uptrend_weakening(self) -> bool:
        """
        Detect if uptrend is weakening (higher lows but lower high).
        This is a potential reversal signal and good for SHORT entries.

        Returns:
            True if uptrend is weakening
        """
        return self.is_higher_low() and self.is_lower_high()

    def is_downtrend_weakening(self) -> bool:
        """
        Detect if downtrend is weakening (lower highs but higher low).
        This is a potential reversal signal and good for LONG entries.

        Returns:
            True if downtrend is weakening
        """
        return self.is_lower_high() and self.is_higher_low()

    def get_higher_low_level(self) -> Optional[float]:
        """
        Get the price level of the higher low.
        This is a key level for SHORT entries when bearish signals appear.

        Returns:
            Price of the higher low, or None if not available
        """
        if not self.is_higher_low():
            return None
        return self.swing_lows[-1].price

    def get_lower_high_level(self) -> Optional[float]:
        """
        Get the price level of the lower high.
        This is a key level for SHORT confirmation.

        Returns:
            Price of the lower high, or None if not available
        """
        if not self.is_lower_high():
            return None
        return self.swing_highs[-1].price

    def should_enter_short_at_higher_low(
        self,
        current_price: float,
        tolerance: float = 0.005
    ) -> Tuple[bool, Optional[float]]:
        """
        Determine if we should enter a SHORT position at the higher low level.

        This is the key method for the requested feature:
        - When we have a higher low (still in uptrend structure)
        - But bearish signals appear (whale distribution, etc.)
        - We enter SHORT at this level anticipating trend reversal

        Args:
            current_price: Current market price
            tolerance: Price tolerance (default 0.5%)

        Returns:
            Tuple of (should_enter, entry_price)
        """
        higher_low = self.get_higher_low_level()
        if higher_low is None:
            return False, None

        # Check if current price is near the higher low level
        price_diff = abs(current_price - higher_low) / higher_low
        if price_diff <= tolerance:
            return True, higher_low

        return False, None

    def get_short_entry_conditions(
        self,
        current_price: float,
        tolerance: float = 0.005
    ) -> dict:
        """
        Get detailed conditions for SHORT entry at higher low level.

        Args:
            current_price: Current market price
            tolerance: Price tolerance

        Returns:
            Dictionary with entry conditions
        """
        should_enter, entry_price = self.should_enter_short_at_higher_low(
            current_price, tolerance
        )

        last_high = self.get_last_swing_high()
        last_low = self.get_last_swing_low()

        return {
            "should_enter_short": should_enter,
            "entry_level": entry_price,
            "is_higher_low": self.is_higher_low(),
            "is_lower_high": self.is_lower_high(),
            "uptrend_weakening": self.is_uptrend_weakening(),
            "last_swing_high": last_high.price if last_high else None,
            "last_swing_low": last_low.price if last_low else None,
            "stop_loss_suggestion": last_high.price if last_high else None,
            "trend": "uptrend" if self.is_uptrend() else (
                "downtrend" if self.is_downtrend() else (
                    "weakening_uptrend" if self.is_uptrend_weakening() else "uncertain"
                )
            )
        }

    def reset(self):
        """Reset swing point detector to initial state."""
        super().reset()
        self.swing_highs = []
        self.swing_lows = []
