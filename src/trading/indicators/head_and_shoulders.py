"""
Head and Shoulders Pattern Detector.

Identifies classic Head & Shoulders reversal patterns.
"""
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime
from .base_indicator import BaseIndicator, Candle


@dataclass
class HeadAndShouldersPattern:
    """Represents a detected Head & Shoulders pattern."""
    left_shoulder_idx: int
    head_idx: int
    right_shoulder_idx: int
    neckline_price: float
    left_shoulder_price: float
    head_price: float
    right_shoulder_price: float
    pattern_height: float  # Distance from head to neckline
    target_price: float  # Projected target
    is_inverse: bool  # True for inverse H&S (bullish)
    timestamp: datetime

    def get_breakdown_entry(self, tolerance: float = 0.005) -> float:
        """Get entry price on neckline break (slightly below for confirmation)."""
        if self.is_inverse:
            return self.neckline_price * (1 + tolerance)  # Break above
        else:
            return self.neckline_price * (1 - tolerance)  # Break below


class HeadAndShoulders(BaseIndicator):
    """
    Head and Shoulders pattern detector.

    Detects both regular (bearish) and inverse (bullish) patterns.
    """

    def __init__(self, lookback: int = 100, min_pattern_width: int = 20):
        """
        Initialize Head and Shoulders detector.

        Args:
            lookback: Number of candles to analyze
            min_pattern_width: Minimum width of pattern in candles
        """
        super().__init__(period=lookback)
        self.lookback = lookback
        self.min_pattern_width = min_pattern_width
        self.detected_pattern: Optional[HeadAndShouldersPattern] = None

    def calculate(self, candles: List[Candle]) -> Optional[float]:
        """
        Detect Head and Shoulders pattern.

        Args:
            candles: List of Candle objects

        Returns:
            Neckline price if pattern detected, None otherwise
        """
        if len(candles) < self.lookback:
            return None

        recent_candles = candles[-self.lookback:]

        # Try to detect regular H&S (bearish)
        pattern = self._detect_regular_hs(recent_candles)
        if pattern:
            self.detected_pattern = pattern
            return pattern.neckline_price

        # Try to detect inverse H&S (bullish)
        pattern = self._detect_inverse_hs(recent_candles)
        if pattern:
            self.detected_pattern = pattern
            return pattern.neckline_price

        self.detected_pattern = None
        return None

    def _detect_regular_hs(self, candles: List[Candle]) -> Optional[HeadAndShouldersPattern]:
        """
        Detect regular (bearish) Head and Shoulders.

        Pattern characteristics:
        - Three peaks (left shoulder, head, right shoulder)
        - Head is highest
        - Shoulders at similar heights
        - Neckline connects the lows between peaks
        """
        # Find all local peaks (highs)
        peaks = self._find_local_peaks(candles, find_highs=True)

        if len(peaks) < 3:
            return None

        # Try different combinations of 3 peaks
        for i in range(len(peaks) - 2):
            left_shoulder_idx = peaks[i]
            head_idx = peaks[i + 1]
            right_shoulder_idx = peaks[i + 2]

            # Check pattern width
            pattern_width = right_shoulder_idx - left_shoulder_idx
            if pattern_width < self.min_pattern_width:
                continue

            left_shoulder_price = candles[left_shoulder_idx].high
            head_price = candles[head_idx].high
            right_shoulder_price = candles[right_shoulder_idx].high

            # Head must be highest
            if head_price <= left_shoulder_price or head_price <= right_shoulder_price:
                continue

            # Shoulders should be at similar heights (within 5%)
            shoulder_diff = abs(left_shoulder_price - right_shoulder_price)
            avg_shoulder = (left_shoulder_price + right_shoulder_price) / 2
            if shoulder_diff / avg_shoulder > 0.05:
                continue

            # Find neckline (lows between peaks)
            neckline_price = self._calculate_neckline(
                candles, left_shoulder_idx, head_idx, right_shoulder_idx
            )

            if neckline_price is None:
                continue

            # Pattern height (from head to neckline)
            pattern_height = head_price - neckline_price

            # Target price (project pattern height below neckline)
            target_price = neckline_price - pattern_height

            return HeadAndShouldersPattern(
                left_shoulder_idx=left_shoulder_idx,
                head_idx=head_idx,
                right_shoulder_idx=right_shoulder_idx,
                neckline_price=neckline_price,
                left_shoulder_price=left_shoulder_price,
                head_price=head_price,
                right_shoulder_price=right_shoulder_price,
                pattern_height=pattern_height,
                target_price=target_price,
                is_inverse=False,
                timestamp=candles[-1].timestamp
            )

        return None

    def _detect_inverse_hs(self, candles: List[Candle]) -> Optional[HeadAndShouldersPattern]:
        """
        Detect inverse (bullish) Head and Shoulders.

        Pattern characteristics:
        - Three troughs (left shoulder, head, right shoulder)
        - Head is lowest
        - Shoulders at similar depths
        - Neckline connects the highs between troughs
        """
        # Find all local troughs (lows)
        troughs = self._find_local_peaks(candles, find_highs=False)

        if len(troughs) < 3:
            return None

        # Try different combinations of 3 troughs
        for i in range(len(troughs) - 2):
            left_shoulder_idx = troughs[i]
            head_idx = troughs[i + 1]
            right_shoulder_idx = troughs[i + 2]

            # Check pattern width
            pattern_width = right_shoulder_idx - left_shoulder_idx
            if pattern_width < self.min_pattern_width:
                continue

            left_shoulder_price = candles[left_shoulder_idx].low
            head_price = candles[head_idx].low
            right_shoulder_price = candles[right_shoulder_idx].low

            # Head must be lowest
            if head_price >= left_shoulder_price or head_price >= right_shoulder_price:
                continue

            # Shoulders should be at similar depths (within 5%)
            shoulder_diff = abs(left_shoulder_price - right_shoulder_price)
            avg_shoulder = (left_shoulder_price + right_shoulder_price) / 2
            if shoulder_diff / avg_shoulder > 0.05:
                continue

            # Find neckline (highs between troughs)
            neckline_price = self._calculate_neckline_inverse(
                candles, left_shoulder_idx, head_idx, right_shoulder_idx
            )

            if neckline_price is None:
                continue

            # Pattern height (from neckline to head)
            pattern_height = neckline_price - head_price

            # Target price (project pattern height above neckline)
            target_price = neckline_price + pattern_height

            return HeadAndShouldersPattern(
                left_shoulder_idx=left_shoulder_idx,
                head_idx=head_idx,
                right_shoulder_idx=right_shoulder_idx,
                neckline_price=neckline_price,
                left_shoulder_price=left_shoulder_price,
                head_price=head_price,
                right_shoulder_price=right_shoulder_price,
                pattern_height=pattern_height,
                target_price=target_price,
                is_inverse=True,
                timestamp=candles[-1].timestamp
            )

        return None

    def _find_local_peaks(self, candles: List[Candle], find_highs: bool = True, window: int = 5) -> List[int]:
        """
        Find local peaks (highs) or troughs (lows) in the data.

        Args:
            candles: List of candles
            find_highs: True to find peaks, False to find troughs
            window: Window size for peak detection

        Returns:
            List of indices where peaks/troughs occur
        """
        peaks = []

        for i in range(window, len(candles) - window):
            if find_highs:
                # Check if this is a local high
                is_peak = all(
                    candles[i].high >= candles[j].high
                    for j in range(i - window, i + window + 1)
                    if j != i
                )
            else:
                # Check if this is a local low
                is_peak = all(
                    candles[i].low <= candles[j].low
                    for j in range(i - window, i + window + 1)
                    if j != i
                )

            if is_peak:
                peaks.append(i)

        return peaks

    def _calculate_neckline(
        self,
        candles: List[Candle],
        left_idx: int,
        head_idx: int,
        right_idx: int
    ) -> Optional[float]:
        """
        Calculate neckline for regular H&S (connects lows between peaks).

        Args:
            candles: List of candles
            left_idx: Left shoulder index
            head_idx: Head index
            right_idx: Right shoulder index

        Returns:
            Neckline price
        """
        # Find low between left shoulder and head
        left_low_idx = left_idx + min(range(left_idx, head_idx),
                                      key=lambda i: candles[i].low if i < len(candles) else float('inf'))

        # Find low between head and right shoulder
        right_low_idx = head_idx + min(range(head_idx, right_idx),
                                       key=lambda i: candles[i].low if i < len(candles) else float('inf'))

        if left_low_idx >= len(candles) or right_low_idx >= len(candles):
            return None

        # Neckline is average of these two lows
        neckline = (candles[left_low_idx].low + candles[right_low_idx].low) / 2

        return neckline

    def _calculate_neckline_inverse(
        self,
        candles: List[Candle],
        left_idx: int,
        head_idx: int,
        right_idx: int
    ) -> Optional[float]:
        """
        Calculate neckline for inverse H&S (connects highs between troughs).

        Args:
            candles: List of candles
            left_idx: Left shoulder index
            head_idx: Head index
            right_idx: Right shoulder index

        Returns:
            Neckline price
        """
        # Find high between left shoulder and head
        left_high_idx = left_idx + max(range(left_idx, head_idx),
                                       key=lambda i: candles[i].high if i < len(candles) else float('-inf'))

        # Find high between head and right shoulder
        right_high_idx = head_idx + max(range(head_idx, right_idx),
                                        key=lambda i: candles[i].high if i < len(candles) else float('-inf'))

        if left_high_idx >= len(candles) or right_high_idx >= len(candles):
            return None

        # Neckline is average of these two highs
        neckline = (candles[left_high_idx].high + candles[right_high_idx].high) / 2

        return neckline

    def has_pattern(self) -> bool:
        """Check if a pattern is currently detected."""
        return self.detected_pattern is not None

    def is_bearish_pattern(self) -> bool:
        """Check if detected pattern is bearish (regular H&S)."""
        return self.detected_pattern is not None and not self.detected_pattern.is_inverse

    def is_bullish_pattern(self) -> bool:
        """Check if detected pattern is bullish (inverse H&S)."""
        return self.detected_pattern is not None and self.detected_pattern.is_inverse

    def get_pattern(self) -> Optional[HeadAndShouldersPattern]:
        """Get the detected pattern."""
        return self.detected_pattern

    def neckline_broken(self, current_price: float, tolerance: float = 0.005) -> bool:
        """
        Check if neckline has been broken (pattern activated).

        Args:
            current_price: Current price
            tolerance: Price tolerance for break confirmation

        Returns:
            True if neckline broken in pattern direction
        """
        if not self.detected_pattern:
            return False

        neckline = self.detected_pattern.neckline_price

        if self.detected_pattern.is_inverse:
            # Inverse H&S: breakout above neckline
            return current_price > neckline * (1 + tolerance)
        else:
            # Regular H&S: breakdown below neckline
            return current_price < neckline * (1 - tolerance)

    def failed_retest(self, candles: List[Candle], tolerance: float = 0.01) -> bool:
        """
        Check if there was a failed retest of neckline after break.

        This confirms the pattern strength.

        Args:
            candles: Recent candles
            tolerance: Price tolerance

        Returns:
            True if failed retest detected
        """
        if not self.detected_pattern or len(candles) < 5:
            return False

        neckline = self.detected_pattern.neckline_price
        recent_candles = candles[-5:]

        if self.detected_pattern.is_inverse:
            # After breaking above, price should not close back below neckline
            # Look for a retest that failed to break back below
            for candle in recent_candles:
                # Price touched neckline from above
                if abs(candle.low - neckline) <= neckline * tolerance:
                    # But closed above it
                    if candle.close > neckline:
                        return True
        else:
            # After breaking below, price should not close back above neckline
            # Look for a retest that failed to break back above
            for candle in recent_candles:
                # Price touched neckline from below
                if abs(candle.high - neckline) <= neckline * tolerance:
                    # But closed below it
                    if candle.close < neckline:
                        return True

        return False

    def validate_volume_pattern(self, candles: List[Candle]) -> bool:
        """
        Validate volume pattern (decreasing from left shoulder to right shoulder).

        Classic H&S has:
        - High volume on left shoulder
        - Lower volume on head
        - Minimum volume on right shoulder

        Args:
            candles: List of candles

        Returns:
            True if volume pattern is valid
        """
        if not self.detected_pattern:
            return False

        pattern = self.detected_pattern

        # Get volumes at each peak
        left_volume = candles[pattern.left_shoulder_idx].volume
        head_volume = candles[pattern.head_idx].volume
        right_volume = candles[pattern.right_shoulder_idx].volume

        # Volume should decrease: left > head > right (approximately)
        # Allow some tolerance
        return left_volume > head_volume * 0.8 and head_volume > right_volume * 0.8
