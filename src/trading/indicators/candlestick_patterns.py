"""
Candlestick Pattern Detector.

Identifies common candlestick patterns used for entry/exit signals.
"""
from typing import List, Optional, Dict
from .base_indicator import BaseIndicator, Candle


class CandlestickPatterns(BaseIndicator):
    """
    Detects common candlestick patterns.

    Patterns detected:
    - Hammer (bullish reversal)
    - Shooting Star (bearish reversal)
    - Bullish Engulfing
    - Bearish Engulfing
    - Dark Cloud Cover (bearish)
    - Piercing Pattern (bullish)
    - Doji (indecision)
    - Morning Star (bullish reversal)
    - Evening Star (bearish reversal)
    """

    def __init__(self):
        """Initialize Candlestick Pattern detector."""
        super().__init__(period=3)  # Most patterns need 2-3 candles
        self.detected_patterns: List[str] = []

    def calculate(self, candles: List[Candle]) -> Optional[float]:
        """
        Detect patterns in recent candles.

        Args:
            candles: List of Candle objects

        Returns:
            Pattern strength score (0-100) or None
        """
        if len(candles) < 3:
            return None

        self.detected_patterns = []
        score = 0

        # Check all patterns
        if self.is_hammer(candles[-1]):
            self.detected_patterns.append('hammer')
            score += 30

        if self.is_shooting_star(candles[-1]):
            self.detected_patterns.append('shooting_star')
            score += 30

        if len(candles) >= 2:
            if self.is_bullish_engulfing(candles[-2], candles[-1]):
                self.detected_patterns.append('bullish_engulfing')
                score += 40

            if self.is_bearish_engulfing(candles[-2], candles[-1]):
                self.detected_patterns.append('bearish_engulfing')
                score += 40

            if self.is_dark_cloud_cover(candles[-2], candles[-1]):
                self.detected_patterns.append('dark_cloud_cover')
                score += 35

            if self.is_piercing_pattern(candles[-2], candles[-1]):
                self.detected_patterns.append('piercing_pattern')
                score += 35

        if self.is_doji(candles[-1]):
            self.detected_patterns.append('doji')
            score += 15

        if len(candles) >= 3:
            if self.is_morning_star(candles[-3], candles[-2], candles[-1]):
                self.detected_patterns.append('morning_star')
                score += 50

            if self.is_evening_star(candles[-3], candles[-2], candles[-1]):
                self.detected_patterns.append('evening_star')
                score += 50

        return min(score, 100)  # Cap at 100

    def is_hammer(self, candle: Candle, min_body_ratio: float = 0.25) -> bool:
        """
        Detect Hammer pattern (bullish reversal).

        Characteristics:
        - Small body at top of range
        - Long lower shadow (2x+ body)
        - Little to no upper shadow

        Args:
            candle: Candle to check
            min_body_ratio: Minimum body size relative to range

        Returns:
            True if hammer pattern detected
        """
        if candle.range == 0:
            return False

        body = candle.body_size
        lower_shadow = abs(min(candle.open, candle.close) - candle.low)
        upper_shadow = abs(candle.high - max(candle.open, candle.close))

        # Body is small relative to range
        body_ratio = body / candle.range
        if body_ratio > 0.3:
            return False

        # Long lower shadow
        if lower_shadow < body * 2:
            return False

        # Small upper shadow
        if upper_shadow > body:
            return False

        return True

    def is_shooting_star(self, candle: Candle) -> bool:
        """
        Detect Shooting Star pattern (bearish reversal).

        Characteristics:
        - Small body at bottom of range
        - Long upper shadow (2x+ body)
        - Little to no lower shadow

        Args:
            candle: Candle to check

        Returns:
            True if shooting star pattern detected
        """
        if candle.range == 0:
            return False

        body = candle.body_size
        upper_shadow = abs(candle.high - max(candle.open, candle.close))
        lower_shadow = abs(min(candle.open, candle.close) - candle.low)

        # Body is small relative to range
        body_ratio = body / candle.range
        if body_ratio > 0.3:
            return False

        # Long upper shadow
        if upper_shadow < body * 2:
            return False

        # Small lower shadow
        if lower_shadow > body:
            return False

        return True

    def is_bullish_engulfing(self, prev_candle: Candle, current_candle: Candle) -> bool:
        """
        Detect Bullish Engulfing pattern.

        Characteristics:
        - Previous candle is bearish
        - Current candle is bullish
        - Current candle body completely engulfs previous body

        Args:
            prev_candle: Previous candle
            current_candle: Current candle

        Returns:
            True if bullish engulfing detected
        """
        # Previous must be bearish
        if not prev_candle.is_bearish:
            return False

        # Current must be bullish
        if not current_candle.is_bullish:
            return False

        # Current body engulfs previous body
        prev_body_top = max(prev_candle.open, prev_candle.close)
        prev_body_bottom = min(prev_candle.open, prev_candle.close)
        curr_body_top = max(current_candle.open, current_candle.close)
        curr_body_bottom = min(current_candle.open, current_candle.close)

        return (curr_body_bottom < prev_body_bottom and
                curr_body_top > prev_body_top)

    def is_bearish_engulfing(self, prev_candle: Candle, current_candle: Candle) -> bool:
        """
        Detect Bearish Engulfing pattern.

        Characteristics:
        - Previous candle is bullish
        - Current candle is bearish
        - Current candle body completely engulfs previous body

        Args:
            prev_candle: Previous candle
            current_candle: Current candle

        Returns:
            True if bearish engulfing detected
        """
        # Previous must be bullish
        if not prev_candle.is_bullish:
            return False

        # Current must be bearish
        if not current_candle.is_bearish:
            return False

        # Current body engulfs previous body
        prev_body_top = max(prev_candle.open, prev_candle.close)
        prev_body_bottom = min(prev_candle.open, prev_candle.close)
        curr_body_top = max(current_candle.open, current_candle.close)
        curr_body_bottom = min(current_candle.open, current_candle.close)

        return (curr_body_bottom < prev_body_bottom and
                curr_body_top > prev_body_top)

    def is_dark_cloud_cover(self, prev_candle: Candle, current_candle: Candle) -> bool:
        """
        Detect Dark Cloud Cover pattern (bearish reversal).

        Characteristics:
        - Previous candle is bullish
        - Current candle is bearish
        - Current opens above previous high
        - Current closes below midpoint of previous body

        Args:
            prev_candle: Previous candle
            current_candle: Current candle

        Returns:
            True if dark cloud cover detected
        """
        if not prev_candle.is_bullish or not current_candle.is_bearish:
            return False

        # Current opens above previous high
        if current_candle.open <= prev_candle.high:
            return False

        # Current closes below midpoint of previous body
        prev_midpoint = (prev_candle.open + prev_candle.close) / 2
        if current_candle.close >= prev_midpoint:
            return False

        return True

    def is_piercing_pattern(self, prev_candle: Candle, current_candle: Candle) -> bool:
        """
        Detect Piercing Pattern (bullish reversal).

        Characteristics:
        - Previous candle is bearish
        - Current candle is bullish
        - Current opens below previous low
        - Current closes above midpoint of previous body

        Args:
            prev_candle: Previous candle
            current_candle: Current candle

        Returns:
            True if piercing pattern detected
        """
        if not prev_candle.is_bearish or not current_candle.is_bullish:
            return False

        # Current opens below previous low
        if current_candle.open >= prev_candle.low:
            return False

        # Current closes above midpoint of previous body
        prev_midpoint = (prev_candle.open + prev_candle.close) / 2
        if current_candle.close <= prev_midpoint:
            return False

        return True

    def is_doji(self, candle: Candle, max_body_ratio: float = 0.1) -> bool:
        """
        Detect Doji pattern (indecision).

        Characteristics:
        - Very small body (open ≈ close)
        - Can have shadows of any length

        Args:
            candle: Candle to check
            max_body_ratio: Maximum body size relative to range

        Returns:
            True if doji detected
        """
        if candle.range == 0:
            return False

        body_ratio = candle.body_size / candle.range
        return body_ratio <= max_body_ratio

    def is_morning_star(
        self,
        first: Candle,
        second: Candle,
        third: Candle
    ) -> bool:
        """
        Detect Morning Star pattern (bullish reversal).

        Characteristics:
        - First candle: Large bearish
        - Second candle: Small body (doji-like), gaps down
        - Third candle: Large bullish, closes above first's midpoint

        Args:
            first: First candle
            second: Second candle
            third: Third candle

        Returns:
            True if morning star detected
        """
        # First must be bearish
        if not first.is_bearish:
            return False

        # Second must be small (doji-like)
        if not self.is_doji(second, max_body_ratio=0.3):
            return False

        # Third must be bullish
        if not third.is_bullish:
            return False

        # Third must be strong
        if third.body_size < first.body_size * 0.5:
            return False

        # Third closes above first's midpoint
        first_midpoint = (first.open + first.close) / 2
        if third.close <= first_midpoint:
            return False

        return True

    def is_evening_star(
        self,
        first: Candle,
        second: Candle,
        third: Candle
    ) -> bool:
        """
        Detect Evening Star pattern (bearish reversal).

        Characteristics:
        - First candle: Large bullish
        - Second candle: Small body (doji-like), gaps up
        - Third candle: Large bearish, closes below first's midpoint

        Args:
            first: First candle
            second: Second candle
            third: Third candle

        Returns:
            True if evening star detected
        """
        # First must be bullish
        if not first.is_bullish:
            return False

        # Second must be small (doji-like)
        if not self.is_doji(second, max_body_ratio=0.3):
            return False

        # Third must be bearish
        if not third.is_bearish:
            return False

        # Third must be strong
        if third.body_size < first.body_size * 0.5:
            return False

        # Third closes below first's midpoint
        first_midpoint = (first.open + first.close) / 2
        if third.close >= first_midpoint:
            return False

        return True

    def has_bullish_pattern(self) -> bool:
        """Check if any bullish patterns were detected."""
        bullish_patterns = {
            'hammer', 'bullish_engulfing', 'piercing_pattern', 'morning_star'
        }
        return bool(bullish_patterns & set(self.detected_patterns))

    def has_bearish_pattern(self) -> bool:
        """Check if any bearish patterns were detected."""
        bearish_patterns = {
            'shooting_star', 'bearish_engulfing', 'dark_cloud_cover', 'evening_star'
        }
        return bool(bearish_patterns & set(self.detected_patterns))

    def get_patterns(self) -> List[str]:
        """Get list of all detected patterns."""
        return self.detected_patterns.copy()

    def get_pattern_details(self) -> Dict[str, bool]:
        """Get detailed pattern detection results."""
        return {
            'hammer': 'hammer' in self.detected_patterns,
            'shooting_star': 'shooting_star' in self.detected_patterns,
            'bullish_engulfing': 'bullish_engulfing' in self.detected_patterns,
            'bearish_engulfing': 'bearish_engulfing' in self.detected_patterns,
            'dark_cloud_cover': 'dark_cloud_cover' in self.detected_patterns,
            'piercing_pattern': 'piercing_pattern' in self.detected_patterns,
            'doji': 'doji' in self.detected_patterns,
            'morning_star': 'morning_star' in self.detected_patterns,
            'evening_star': 'evening_star' in self.detected_patterns,
        }
