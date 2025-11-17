"""
LONG Entry Strategy 5: Fibonacci + Accumulation.

Entry conditions:
1. Retracement 0.618-0.786 from last impulse
2. Consolidation 8-12 candles on operational timeframe
3. Decreasing volume in consolidation
4. Entry: range high breakout with 1.5x average volume
"""
from typing import List, Optional
from .base_strategy import BaseStrategy, TradingSignal, SignalType, SignalStrength
from ..indicators import Candle
from ..indicators.fibonacci import FibonacciRetracement


class LongFibonacciAccumulationStrategy(BaseStrategy):
    """
    LONG Entry Strategy 5: Fibonacci + Accumulation.

    Optimal for:
    - Golden zone (0.618-0.786) reversals
    - Accumulation breakouts after retracement
    """

    def __init__(
        self,
        fib_lookback: int = 50,
        min_consolidation_candles: int = 8,
        max_consolidation_candles: int = 12,
        volume_threshold: float = 1.5,  # 1.5x average volume
        timeframe: str = "15m"
    ):
        """
        Initialize Fibonacci Accumulation LONG strategy.

        Args:
            fib_lookback: Lookback for Fibonacci calculation
            min_consolidation_candles: Minimum consolidation period
            max_consolidation_candles: Maximum consolidation period
            volume_threshold: Volume multiplier for breakout
            timeframe: Trading timeframe
        """
        super().__init__(name="LONG_Fibonacci_Accumulation", timeframe=timeframe)
        self.fibonacci = FibonacciRetracement(lookback=fib_lookback)
        self.min_consolidation = min_consolidation_candles
        self.max_consolidation = max_consolidation_candles
        self.volume_threshold = volume_threshold
        self.min_candles = fib_lookback + max_consolidation_candles

    def analyze(self, candles: List[Candle]) -> Optional[TradingSignal]:
        """
        Analyze candles for Fibonacci accumulation entry setup.

        Args:
            candles: List of Candle objects

        Returns:
            TradingSignal if conditions met, None otherwise
        """
        if not self.is_ready() or len(candles) < self.min_candles:
            return None

        # Update indicators
        self.fibonacci.calculate(candles)

        current_candle = candles[-1]
        current_price = current_candle.close

        # 1. Check if price in golden zone (0.618-0.786)
        in_golden_zone = self.fibonacci.is_in_golden_zone(current_price)
        if not in_golden_zone:
            # Also accept 0.618 level specifically
            at_618 = self.fibonacci.is_at_level(current_price, '0.618', tolerance=0.01)
            if not at_618:
                return None

        # 2. Check for consolidation (8-12 candles)
        consolidation_length = self._check_consolidation(candles)
        if consolidation_length < self.min_consolidation:
            return None

        # 3. Check decreasing volume in consolidation
        volume_decreasing = self._check_decreasing_volume(candles, consolidation_length)

        # 4. Check for range high breakout with volume
        breakout, volume_expansion = self._check_range_breakout(candles, consolidation_length)
        if not breakout:
            return None

        # Calculate strength score
        strength_score = 0
        reasons = []

        if in_golden_zone:
            strength_score += 35
            retracement = self.fibonacci.get_retracement_depth(current_price)
            reasons.append(f"Price in Fibonacci golden zone (retracement: {retracement * 100:.1f}%)")
        else:
            strength_score += 30
            reasons.append("Price at Fibonacci 0.618 level (key retracement)")

        if consolidation_length >= self.min_consolidation:
            strength_score += 20
            reasons.append(f"Consolidation formed ({consolidation_length} candles)")

        if volume_decreasing:
            strength_score += 15
            reasons.append("Volume decreasing in consolidation (accumulation)")

        if breakout:
            strength_score += 20
            reasons.append("Range high breakout (accumulation complete)")

        if volume_expansion >= self.volume_threshold:
            strength_score += 10
            reasons.append(f"Expansive volume on breakout ({volume_expansion:.1f}x average)")

        # Calculate stop loss and take profit
        # Stop below Fibonacci 0.786 or swing low
        fib_786 = self.fibonacci.levels_cache.get('0.786')
        swing_low = self._get_consolidation_low(candles, consolidation_length)

        if fib_786:
            stop_loss = min(fib_786, swing_low) * 0.99
        else:
            stop_loss = swing_low * 0.99

        risk = current_price - stop_loss

        # Ensure risk is reasonable (max 3% from entry)
        if risk / current_price > 0.03:
            return None

        # Target: Fibonacci 0.0 level (impulse high) or 2.5:1 R/R
        fib_000 = self.fibonacci.levels_cache.get('0.0')
        if fib_000:
            take_profit = min(fib_000, current_price + (risk * 2.5))
        else:
            take_profit = current_price + (risk * 2.5)

        # Map score to signal strength
        if strength_score >= 80:
            signal_strength = SignalStrength.VERY_STRONG
        elif strength_score >= 60:
            signal_strength = SignalStrength.STRONG
        elif strength_score >= 40:
            signal_strength = SignalStrength.MEDIUM
        else:
            signal_strength = SignalStrength.WEAK

        # Create signal
        signal = TradingSignal(
            signal_type=SignalType.LONG,
            strength=signal_strength,
            price=current_price,
            timestamp=current_candle.timestamp,
            strategy_name=self.name,
            reasons=reasons,
            indicators={
                'fib_levels': self.fibonacci.get_levels(),
                'fib_618': self.fibonacci.levels_cache.get('0.618'),
                'fib_786': self.fibonacci.levels_cache.get('0.786'),
                'consolidation_candles': consolidation_length,
                'volume_expansion': volume_expansion,
                'retracement_depth': self.fibonacci.get_retracement_depth(current_price),
            },
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=(take_profit - current_price) / risk if risk > 0 else 2.5
        )

        self.add_signal(signal)
        return signal

    def _check_consolidation(self, candles: List[Candle], max_lookback: int = 20) -> int:
        """
        Check for consolidation and return its length.

        Args:
            candles: List of candles
            max_lookback: Maximum lookback period

        Returns:
            Number of consolidation candles (0 if no consolidation)
        """
        if len(candles) < self.min_consolidation:
            return 0

        # Look for consolidation in recent candles
        for length in range(self.max_consolidation, self.min_consolidation - 1, -1):
            if len(candles) < length:
                continue

            consolidation_candles = candles[-length:]
            closes = [c.close for c in consolidation_candles]

            # Check if range is tight
            high = max(closes)
            low = min(closes)
            range_pct = (high - low) / low

            # Consolidation if range < 3%
            if range_pct < 0.03:
                return length

        return 0

    def _check_decreasing_volume(self, candles: List[Candle], consolidation_length: int) -> bool:
        """
        Check if volume is decreasing during consolidation.

        Args:
            candles: List of candles
            consolidation_length: Length of consolidation period

        Returns:
            True if volume decreasing
        """
        if len(candles) < consolidation_length:
            return False

        consolidation_candles = candles[-consolidation_length:]
        volumes = [c.volume for c in consolidation_candles]

        # Compare first half vs second half
        mid = len(volumes) // 2
        first_half_avg = sum(volumes[:mid]) / mid if mid > 0 else 0
        second_half_avg = sum(volumes[mid:]) / (len(volumes) - mid) if len(volumes) > mid else 0

        if first_half_avg == 0:
            return False

        # Volume should be decreasing
        return second_half_avg < first_half_avg * 0.85  # 15% decrease

    def _check_range_breakout(
        self,
        candles: List[Candle],
        consolidation_length: int
    ) -> tuple[bool, float]:
        """
        Check for range high breakout with volume expansion.

        Args:
            candles: List of candles
            consolidation_length: Length of consolidation

        Returns:
            Tuple of (breakout_occurred, volume_expansion_ratio)
        """
        if len(candles) < consolidation_length + 1:
            return False, 0.0

        # Get consolidation range
        consolidation_candles = candles[-consolidation_length - 1:-1]
        range_high = max(c.high for c in consolidation_candles)

        # Current candle should break above range high
        current_candle = candles[-1]
        breakout = current_candle.close > range_high

        # Calculate volume expansion
        avg_volume = sum(c.volume for c in consolidation_candles) / len(consolidation_candles)
        volume_expansion = current_candle.volume / avg_volume if avg_volume > 0 else 0.0

        return breakout, volume_expansion

    def _get_consolidation_low(self, candles: List[Candle], consolidation_length: int) -> float:
        """
        Get the low of the consolidation range.

        Args:
            candles: List of candles
            consolidation_length: Consolidation period

        Returns:
            Consolidation low price
        """
        if len(candles) < consolidation_length:
            consolidation_length = len(candles)

        consolidation_candles = candles[-consolidation_length:]
        return min(c.low for c in consolidation_candles)

    def is_ready(self) -> bool:
        """Check if strategy has enough data."""
        return self.fibonacci.levels_cache != {}
