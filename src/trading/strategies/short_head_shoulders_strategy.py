"""
SHORT Entry Strategy 4: Head & Shoulders (EmperorBTC pattern).

Entry conditions:
1. Clearly defined neckline
2. Volume: high on left shoulder, lower on head, minimum on right shoulder
3. Entry: neckline break + failed retest
4. Target: head-neckline distance projected downward
"""
from typing import List, Optional
from .base_strategy import BaseStrategy, TradingSignal, SignalType, SignalStrength
from ..indicators import Candle
from ..indicators.head_and_shoulders import HeadAndShoulders


class ShortHeadShouldersStrategy(BaseStrategy):
    """
    SHORT Entry Strategy 4: Head & Shoulders Pattern.

    Optimal for:
    - Major top reversals
    - Classic pattern-based entries with high win rate
    """

    def __init__(
        self,
        lookback: int = 100,
        min_pattern_width: int = 20,
        timeframe: str = "4h"
    ):
        """
        Initialize Head & Shoulders SHORT strategy.

        Args:
            lookback: Lookback for pattern detection
            min_pattern_width: Minimum pattern width in candles
            timeframe: Trading timeframe
        """
        super().__init__(name="SHORT_Head_and_Shoulders", timeframe=timeframe)
        self.hs_detector = HeadAndShoulders(
            lookback=lookback,
            min_pattern_width=min_pattern_width
        )
        self.min_candles = lookback + 10

    def analyze(self, candles: List[Candle]) -> Optional[TradingSignal]:
        """
        Analyze candles for Head & Shoulders entry setup.

        Args:
            candles: List of Candle objects

        Returns:
            TradingSignal if conditions met, None otherwise
        """
        if not self.is_ready() or len(candles) < self.min_candles:
            return None

        # Update indicator
        self.hs_detector.calculate(candles)

        current_candle = candles[-1]
        current_price = current_candle.close

        # 1. Check if H&S pattern detected
        if not self.hs_detector.has_pattern():
            return None

        pattern = self.hs_detector.get_pattern()
        if pattern is None or pattern.is_inverse:
            return None  # Only trade bearish H&S

        # 2. Check volume pattern (decreasing from left to right)
        volume_valid = self.hs_detector.validate_volume_pattern(candles)

        # 3. Check if neckline broken
        neckline_broken = self.hs_detector.neckline_broken(current_price)
        if not neckline_broken:
            return None

        # 4. Check for failed retest
        failed_retest = self.hs_detector.failed_retest(candles)

        # Calculate strength score
        strength_score = 0
        reasons = []

        # Pattern detected
        strength_score += 40
        reasons.append(f"Head & Shoulders pattern detected (neckline: {pattern.neckline_price:.2f})")

        if volume_valid:
            strength_score += 20
            reasons.append("Volume pattern valid (decreasing left → right)")

        if neckline_broken:
            strength_score += 25
            reasons.append(f"Neckline broken at {pattern.neckline_price:.2f}")

        if failed_retest:
            strength_score += 15
            reasons.append("Failed retest of neckline (confirmation)")

        # Calculate stop loss and take profit
        # Stop above neckline or head high
        stop_loss = max(pattern.neckline_price, pattern.head_price) * 1.01

        # Target: project pattern height downward
        take_profit = pattern.target_price

        risk = stop_loss - current_price

        # Ensure risk is reasonable (max 4% for H&S as it's a major pattern)
        if risk / current_price > 0.04:
            # Adjust stop loss if too wide
            stop_loss = current_price * 1.04
            risk = stop_loss - current_price
            take_profit = current_price - (risk * 2.0)

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
                'neckline': pattern.neckline_price,
                'head_price': pattern.head_price,
                'left_shoulder': pattern.left_shoulder_price,
                'right_shoulder': pattern.right_shoulder_price,
                'pattern_height': pattern.pattern_height,
                'target_price': pattern.target_price,
                'volume_valid': volume_valid,
                'failed_retest': failed_retest,
            },
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=(current_price - take_profit) / risk if risk > 0 else 2.0
        )

        self.add_signal(signal)
        return signal

    def is_ready(self) -> bool:
        """Check if strategy has enough data."""
        return True  # H&S detector handles its own readiness
