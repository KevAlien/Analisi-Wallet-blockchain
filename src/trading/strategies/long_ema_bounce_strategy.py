"""
LONG Entry Strategy 2: EMA Bounce + Structure.

Entry conditions:
1. Price retests EMA 200 (4H) or EMA 50 (1H) as support
2. Rejection candle (hammer, bullish engulfing)
3. Price above faster EMAs (20/50)
4. Entry: candle close above EMA + body greater than 50%
"""
from typing import List, Optional
from .base_strategy import BaseStrategy, TradingSignal, SignalType, SignalStrength
from ..indicators import Candle
from ..indicators.ema import EMA
from ..indicators.candlestick_patterns import CandlestickPatterns


class LongEMABounceStrategy(BaseStrategy):
    """
    LONG Entry Strategy 2: EMA Bounce + Structure.

    Optimal for:
    - Trend continuation trades
    - EMA support bounces in established uptrends
    """

    def __init__(
        self,
        slow_ema_period: int = 200,  # 200 for 4H, 50 for 1H
        medium_ema_period: int = 50,
        fast_ema_period: int = 20,
        min_body_ratio: float = 0.5,  # Minimum 50% body size
        timeframe: str = "4h"
    ):
        """
        Initialize EMA Bounce LONG strategy.

        Args:
            slow_ema_period: Slow EMA period (support level)
            medium_ema_period: Medium EMA period
            fast_ema_period: Fast EMA period
            min_body_ratio: Minimum candle body ratio for entry
            timeframe: Trading timeframe
        """
        super().__init__(name="LONG_EMA_Bounce", timeframe=timeframe)
        self.ema_slow = EMA(period=slow_ema_period)
        self.ema_medium = EMA(period=medium_ema_period)
        self.ema_fast = EMA(period=fast_ema_period)
        self.candle_patterns = CandlestickPatterns()
        self.min_body_ratio = min_body_ratio
        self.min_candles = slow_ema_period + 10

    def analyze(self, candles: List[Candle]) -> Optional[TradingSignal]:
        """
        Analyze candles for EMA bounce entry setup.

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
        self.candle_patterns.calculate(candles)

        current_candle = candles[-1]
        prev_candle = candles[-2] if len(candles) >= 2 else None
        current_price = current_candle.close

        ema_slow_val = self.ema_slow.current_value
        ema_medium_val = self.ema_medium.current_value
        ema_fast_val = self.ema_fast.current_value

        if not all([ema_slow_val, ema_medium_val, ema_fast_val]):
            return None

        # 1. Check if price retested slow EMA as support
        ema_retest = self._check_ema_retest(candles, ema_slow_val)
        if not ema_retest:
            return None

        # 2. Check for rejection candle pattern
        has_rejection = self._check_rejection_candle(current_candle, prev_candle)

        # 3. Check if price is above faster EMAs
        above_fast_emas = current_price > ema_fast_val and current_price > ema_medium_val

        # 4. Check candle close above EMA with strong body
        strong_close = self._check_strong_close(current_candle, ema_slow_val)
        if not strong_close:
            return None

        # Calculate strength score
        strength_score = 0
        reasons = []

        if ema_retest:
            strength_score += 30
            reasons.append(f"Price retested EMA {self.ema_slow.period} as support")

        if has_rejection:
            strength_score += 25
            patterns = self.candle_patterns.get_patterns()
            reasons.append(f"Bullish rejection candle detected: {', '.join(patterns)}")

        if above_fast_emas:
            strength_score += 20
            reasons.append(f"Price above faster EMAs ({self.ema_fast.period}/{self.ema_medium.period})")

        if strong_close:
            body_ratio = current_candle.body_size / current_candle.range
            strength_score += 15
            reasons.append(f"Strong bullish close (body: {body_ratio * 100:.1f}%)")

        # Check EMA alignment (bullish structure)
        if ema_fast_val > ema_medium_val > ema_slow_val:
            strength_score += 10
            reasons.append("Bullish EMA alignment (20 > 50 > 200)")

        # Calculate stop loss and take profit
        stop_loss = ema_slow_val * 0.99  # Below EMA with buffer
        risk = current_price - stop_loss

        # Ensure risk is reasonable (max 3% from entry)
        if risk / current_price > 0.03:
            return None

        take_profit = current_price + (risk * 2.5)  # 2.5:1 R/R for EMA bounces

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
                f'ema_{self.ema_slow.period}': ema_slow_val,
                f'ema_{self.ema_medium.period}': ema_medium_val,
                f'ema_{self.ema_fast.period}': ema_fast_val,
                'candle_patterns': self.candle_patterns.get_patterns(),
                'body_ratio': current_candle.body_size / current_candle.range if current_candle.range > 0 else 0,
            },
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=2.5
        )

        self.add_signal(signal)
        return signal

    def _check_ema_retest(self, candles: List[Candle], ema_value: float, tolerance: float = 0.01) -> bool:
        """
        Check if price recently retested the EMA as support.

        Args:
            candles: List of candles
            ema_value: Current EMA value
            tolerance: Price tolerance (1%)

        Returns:
            True if EMA was retested as support
        """
        if len(candles) < 5:
            return False

        # Check recent candles for EMA touch
        recent_candles = candles[-5:]

        for candle in recent_candles:
            # Candle touched EMA (low near or at EMA)
            touched_ema = abs(candle.low - ema_value) <= ema_value * tolerance

            # But closed above it (rejection)
            closed_above = candle.close > ema_value

            if touched_ema and closed_above:
                return True

        return False

    def _check_rejection_candle(
        self,
        current: Candle,
        previous: Optional[Candle]
    ) -> bool:
        """
        Check for bullish rejection candle patterns.

        Args:
            current: Current candle
            previous: Previous candle

        Returns:
            True if rejection pattern detected
        """
        # Check for hammer
        if self.candle_patterns.is_hammer(current):
            return True

        # Check for bullish engulfing
        if previous and self.candle_patterns.is_bullish_engulfing(previous, current):
            return True

        # Check for piercing pattern
        if previous and self.candle_patterns.is_piercing_pattern(previous, current):
            return True

        return False

    def _check_strong_close(self, candle: Candle, ema_value: float) -> bool:
        """
        Check for strong bullish close above EMA.

        Args:
            candle: Candle to check
            ema_value: EMA value

        Returns:
            True if strong close conditions met
        """
        # Candle must close above EMA
        if candle.close <= ema_value:
            return False

        # Candle must be bullish
        if not candle.is_bullish:
            return False

        # Body must be at least min_body_ratio of total range
        if candle.range == 0:
            return False

        body_ratio = candle.body_size / candle.range
        return body_ratio >= self.min_body_ratio

    def is_ready(self) -> bool:
        """Check if strategy has enough data."""
        return (self.ema_slow.is_ready() and
                self.ema_medium.is_ready() and
                self.ema_fast.is_ready())
