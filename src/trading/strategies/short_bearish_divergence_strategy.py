"""
SHORT Entry Strategy 1: Bearish Divergence + Top Signals.

Entry conditions:
1. Price makes Higher High
2. RSI makes Lower High (bearish divergence)
3. Decreasing volume on pump
4. Entry: support breakdown + EMA 200 as resistance
5. Stop: above last high
"""
from typing import List, Optional
from .base_strategy import BaseStrategy, TradingSignal, SignalType, SignalStrength
from ..indicators import Candle
from ..indicators.rsi import RSI
from ..indicators.ema import EMA
from ..indicators.swing_points import SwingPointDetector


class ShortBearishDivergenceStrategy(BaseStrategy):
    """
    SHORT Entry Strategy 1: Bearish Divergence + Top Signals.

    Optimal for:
    - Top reversals from overbought conditions
    - High probability shorts with divergence confirmation
    """

    def __init__(
        self,
        rsi_period: int = 14,
        ema_period: int = 200,
        swing_lookback: int = 20,
        timeframe: str = "15m"
    ):
        """
        Initialize Bearish Divergence SHORT strategy.

        Args:
            rsi_period: RSI calculation period
            ema_period: EMA period for resistance
            swing_lookback: Lookback period for swing point detection
            timeframe: Trading timeframe
        """
        super().__init__(name="SHORT_Bearish_Divergence", timeframe=timeframe)
        self.rsi = RSI(period=rsi_period)
        self.ema = EMA(period=ema_period)
        self.swing_detector = SwingPointDetector(lookback=swing_lookback)
        self.min_candles = max(rsi_period, ema_period, swing_lookback) + 10

    def analyze(self, candles: List[Candle]) -> Optional[TradingSignal]:
        """
        Analyze candles for bearish divergence entry setup.

        Args:
            candles: List of Candle objects

        Returns:
            TradingSignal if conditions met, None otherwise
        """
        if not self.is_ready() or len(candles) < self.min_candles:
            return None

        # Update indicators
        self.rsi.update(candles)
        self.ema.update(candles)
        self.swing_detector.calculate(candles)

        current_candle = candles[-1]
        current_price = current_candle.close
        ema_value = self.ema.current_value

        # 1. Check for bearish divergence (price higher high, RSI lower high)
        has_divergence, div_strength = self._check_bearish_divergence(candles)
        if not has_divergence:
            return None

        # 2. Check decreasing volume on pump
        volume_decreasing = self._check_volume_decreasing(candles)

        # 3. Check support breakdown
        support_break = self._check_support_breakdown(candles)
        if not support_break:
            return None

        # 4. Check EMA 200 as resistance
        ema_resistance = self._check_ema_resistance(current_price, ema_value)

        # Calculate strength score
        strength_score = 0
        reasons = []

        if has_divergence:
            strength_score += div_strength
            reasons.append(f"Bearish RSI divergence detected (strength: {div_strength})")

        if volume_decreasing:
            strength_score += 15
            reasons.append("Volume decreasing on pump (weakness)")

        if support_break:
            strength_score += 25
            reasons.append("Local support broken to downside")

        if ema_resistance:
            strength_score += 20
            reasons.append(f"EMA {self.ema.period} acting as resistance")

        # Check if RSI is overbought
        rsi_value = self.rsi.current_value
        if rsi_value and rsi_value > 70:
            strength_score += 10
            reasons.append(f"RSI overbought ({rsi_value:.1f})")

        # Calculate stop loss and take profit
        swing_high = self._get_recent_swing_high(candles)
        stop_loss = swing_high * 1.005  # Above swing high with buffer
        risk = stop_loss - current_price

        # Ensure risk is reasonable (max 3% from entry)
        if risk / current_price > 0.03:
            return None

        take_profit = current_price - (risk * 2.0)  # 2:1 R/R

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
                'rsi': rsi_value,
                'ema_200': ema_value,
                'swing_high': swing_high,
                'current_volume': current_candle.volume,
                'divergence_strength': div_strength,
            },
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=2.0
        )

        self.add_signal(signal)
        return signal

    def _check_bearish_divergence(self, candles: List[Candle]) -> tuple[bool, int]:
        """
        Check for bearish divergence (price higher high, RSI lower high).

        Returns:
            Tuple of (has_divergence, strength_score)
        """
        if not self.rsi.is_ready() or len(candles) < 20:
            return False, 0

        # Get recent swing highs
        swing_highs = []
        rsi_at_highs = []

        for i in range(len(candles) - 5, max(len(candles) - 50, 0), -1):
            if i < 5 or i >= len(candles) - 2:
                continue

            is_swing_high = all(
                candles[i].high >= candles[j].high
                for j in range(max(0, i - 3), min(len(candles), i + 4))
                if j != i
            )

            if is_swing_high:
                swing_highs.append((i, candles[i].high))

                # Get RSI value at this swing high
                temp_rsi = RSI(period=self.rsi.period)
                temp_rsi.update(candles[:i + 1])
                if temp_rsi.current_value:
                    rsi_at_highs.append((i, temp_rsi.current_value))

        # Need at least 2 swing highs to compare
        if len(swing_highs) < 2 or len(rsi_at_highs) < 2:
            return False, 0

        # Check last two swing highs
        prev_high_idx, prev_high_price = swing_highs[-2]
        curr_high_idx, curr_high_price = swing_highs[-1]

        # Find corresponding RSI values
        prev_rsi = next((rsi for idx, rsi in rsi_at_highs if idx == prev_high_idx), None)
        curr_rsi = next((rsi for idx, rsi in rsi_at_highs if idx == curr_high_idx), None)

        if prev_rsi is None or curr_rsi is None:
            return False, 0

        # Bearish divergence: price makes higher high, RSI makes lower high
        price_higher_high = curr_high_price > prev_high_price
        rsi_lower_high = curr_rsi < prev_rsi

        if price_higher_high and rsi_lower_high:
            # Calculate divergence strength
            price_diff = abs(curr_high_price - prev_high_price) / prev_high_price
            rsi_diff = abs(curr_rsi - prev_rsi)

            # Stronger divergence = higher score
            strength = min(40, int(20 + (price_diff * 100) + (rsi_diff / 2)))

            return True, strength

        return False, 0

    def _check_volume_decreasing(self, candles: List[Candle], lookback: int = 10) -> bool:
        """Check if volume is decreasing on upward move."""
        if len(candles) < lookback:
            return False

        recent_candles = candles[-lookback:]
        volumes = [c.volume for c in recent_candles]

        # Check if volume is trending down
        first_half_avg = sum(volumes[:lookback // 2]) / (lookback // 2)
        second_half_avg = sum(volumes[lookback // 2:]) / (lookback - lookback // 2)

        return second_half_avg < first_half_avg * 0.8

    def _check_support_breakdown(self, candles: List[Candle], lookback: int = 20) -> bool:
        """Check if price broke local support."""
        if len(candles) < lookback + 1:
            return False

        current_price = candles[-1].close
        recent_candles = candles[-lookback - 1:-1]

        # Find local support (recent swing low)
        support = min(c.low for c in recent_candles)

        # Current price should be below support
        return current_price < support

    def _check_ema_resistance(self, price: float, ema_value: Optional[float], tolerance: float = 0.02) -> bool:
        """Check if EMA is acting as resistance."""
        if ema_value is None:
            return False

        # Price should be below or near EMA (rejected from it)
        return price <= ema_value * (1 + tolerance)

    def _get_recent_swing_high(self, candles: List[Candle], lookback: int = 20) -> float:
        """Get the most recent swing high."""
        if len(candles) < lookback:
            lookback = len(candles)

        recent_candles = candles[-lookback:]
        return max(c.high for c in recent_candles)

    def is_ready(self) -> bool:
        """Check if strategy has enough data."""
        return self.rsi.is_ready() and self.ema.is_ready()
