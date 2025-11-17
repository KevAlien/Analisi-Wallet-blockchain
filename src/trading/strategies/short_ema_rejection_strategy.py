"""
SHORT Entry Strategy 2: EMA Rejection + Bearish Structure.

Entry conditions:
1. Price rejected by EMA 200 (candles with long upper wicks)
2. Price below EMA 20/50
3. Death Cross (50 below 200) on higher timeframe
4. Entry: local support break + failed retest
"""
from typing import List, Optional
from .base_strategy import BaseStrategy, TradingSignal, SignalType, SignalStrength
from ..indicators import Candle
from ..indicators.ema import EMA


class ShortEMARejectionStrategy(BaseStrategy):
    """
    SHORT Entry Strategy 2: EMA Rejection + Bearish Structure.

    Optimal for:
    - Trend continuation shorts
    - EMA resistance rejections in established downtrends
    """

    def __init__(
        self,
        slow_ema_period: int = 200,
        medium_ema_period: int = 50,
        fast_ema_period: int = 20,
        min_wick_ratio: float = 0.6,  # Long upper wick (60%+ of range)
        timeframe: str = "4h"
    ):
        """
        Initialize EMA Rejection SHORT strategy.

        Args:
            slow_ema_period: Slow EMA period (resistance level)
            medium_ema_period: Medium EMA period
            fast_ema_period: Fast EMA period
            min_wick_ratio: Minimum upper wick ratio for rejection
            timeframe: Trading timeframe
        """
        super().__init__(name="SHORT_EMA_Rejection", timeframe=timeframe)
        self.ema_slow = EMA(period=slow_ema_period)
        self.ema_medium = EMA(period=medium_ema_period)
        self.ema_fast = EMA(period=fast_ema_period)
        self.min_wick_ratio = min_wick_ratio
        self.min_candles = slow_ema_period + 10

    def analyze(self, candles: List[Candle]) -> Optional[TradingSignal]:
        """
        Analyze candles for EMA rejection entry setup.

        Args:
            candles: List of Candle objects

        Returns:
            TradingSignal if conditions met, None otherwise
        """
        if not self.is_ready() or len(candles) < self.min_candles:
            return None

        # Update indicators
        self.ema_slow.update(candles)
        self.ema_medium.update(candles)
        self.ema_fast.update(candles)

        current_candle = candles[-1]
        current_price = current_candle.close

        ema_slow_val = self.ema_slow.current_value
        ema_medium_val = self.ema_medium.current_value
        ema_fast_val = self.ema_fast.current_value

        if not all([ema_slow_val, ema_medium_val, ema_fast_val]):
            return None

        # 1. Check if price rejected by EMA 200 (long upper wick)
        ema_rejection = self._check_ema_rejection(candles, ema_slow_val)
        if not ema_rejection:
            return None

        # 2. Check if price is below faster EMAs
        below_fast_emas = current_price < ema_fast_val and current_price < ema_medium_val

        # 3. Check for death cross
        death_cross = self._check_death_cross(ema_medium_val, ema_slow_val)

        # 4. Check for local support break + failed retest
        support_break = self._check_support_break_and_retest(candles)
        if not support_break:
            return None

        # Calculate strength score
        strength_score = 0
        reasons = []

        if ema_rejection:
            strength_score += 30
            reasons.append(f"Price rejected by EMA {self.ema_slow.period} (long upper wick)")

        if below_fast_emas:
            strength_score += 20
            reasons.append(f"Price below faster EMAs ({self.ema_fast.period}/{self.ema_medium.period})")

        if death_cross:
            strength_score += 20
            reasons.append(f"Death Cross: EMA {self.ema_medium.period} < EMA {self.ema_slow.period}")

        if support_break:
            strength_score += 25
            reasons.append("Local support broken with failed retest")

        # Check EMA alignment (bearish structure)
        if ema_fast_val < ema_medium_val < ema_slow_val:
            strength_score += 10
            reasons.append("Bearish EMA alignment (20 < 50 < 200)")

        # Calculate stop loss and take profit
        stop_loss = ema_slow_val * 1.01  # Above EMA with buffer
        risk = stop_loss - current_price

        # Ensure risk is reasonable (max 3% from entry)
        if risk / current_price > 0.03:
            return None

        take_profit = current_price - (risk * 2.5)  # 2.5:1 R/R for EMA rejections

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
            signal_type=SignalType.SHORT,
            strength=signal_strength,
            price=current_price,
            timestamp=current_candle.timestamp,
            strategy_name=self.name,
            reasons=reasons,
            indicators={
                f'ema_{self.ema_slow.period}': ema_slow_val,
                f'ema_{self.ema_medium.period}': ema_medium_val,
                f'ema_{self.ema_fast.period}': ema_fast_val,
                'death_cross': death_cross,
                'upper_wick_ratio': self._get_upper_wick_ratio(current_candle),
            },
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=2.5
        )

        self.add_signal(signal)
        return signal

    def _check_ema_rejection(self, candles: List[Candle], ema_value: float, tolerance: float = 0.01) -> bool:
        """
        Check if price was rejected by EMA (long upper wick).

        Args:
            candles: List of candles
            ema_value: Current EMA value
            tolerance: Price tolerance

        Returns:
            True if EMA rejection detected
        """
        if len(candles) < 3:
            return False

        # Check recent candles for rejection pattern
        recent_candles = candles[-3:]

        for candle in recent_candles:
            # Candle high touched EMA
            touched_ema = abs(candle.high - ema_value) <= ema_value * tolerance

            # But closed below it (rejection)
            closed_below = candle.close < ema_value

            # Long upper wick
            upper_wick_ratio = self._get_upper_wick_ratio(candle)
            long_upper_wick = upper_wick_ratio >= self.min_wick_ratio

            if touched_ema and closed_below and long_upper_wick:
                return True

        return False

    def _get_upper_wick_ratio(self, candle: Candle) -> float:
        """Calculate upper wick ratio relative to total range."""
        if candle.range == 0:
            return 0.0

        upper_wick = candle.high - max(candle.open, candle.close)
        return upper_wick / candle.range

    def _check_death_cross(self, ema_medium: float, ema_slow: float) -> bool:
        """Check if death cross occurred (EMA 50 below EMA 200)."""
        return ema_medium < ema_slow

    def _check_support_break_and_retest(self, candles: List[Candle], lookback: int = 20) -> bool:
        """
        Check for local support break with failed retest.

        Args:
            candles: List of candles
            lookback: Lookback period

        Returns:
            True if support broken and retest failed
        """
        if len(candles) < lookback + 5:
            return False

        # Find local support
        support_candles = candles[-lookback - 5:-5]
        support = min(c.low for c in support_candles)

        # Check if support was broken
        recent_candles = candles[-5:]
        broken = any(c.close < support for c in recent_candles)

        if not broken:
            return False

        # Check for failed retest (price tried to go back up but failed)
        current_price = candles[-1].close
        for candle in recent_candles[-3:]:
            # Candle moved up (attempted retest)
            if candle.high > candle.open:
                # But failed (closed lower)
                if candle.close < candle.high:
                    return True

        return False

    def is_ready(self) -> bool:
        """Check if strategy has enough data."""
        return (self.ema_slow.is_ready() and
                self.ema_medium.is_ready() and
                self.ema_fast.is_ready())
