"""
LONG Entry Strategy 1: Bullish Divergence + Confirmations.

Entry conditions:
1. Price makes Lower Low
2. RSI/Oscillator makes Higher Low (bullish divergence)
3. Volume decreasing on retracement
4. Entry: local resistance breakout with expansive volume
5. Stop: below swing low
"""
from typing import List, Optional
from .base_strategy import BaseStrategy, TradingSignal, SignalType, SignalStrength
from ..indicators import Candle
from ..indicators.rsi import RSI
from ..indicators.swing_points import SwingPointDetector


class LongBullishDivergenceStrategy(BaseStrategy):
    """
    LONG Entry Strategy 1: Bullish Divergence + Confirmations.

    Optimal for:
    - Trend reversals from oversold conditions
    - High probability bounces with divergence confirmation
    """

    def __init__(
        self,
        rsi_period: int = 14,
        swing_lookback: int = 20,
        volume_threshold: float = 1.5,  # 1.5x average volume for breakout
        timeframe: str = "15m"
    ):
        """
        Initialize Bullish Divergence LONG strategy.

        Args:
            rsi_period: RSI calculation period
            swing_lookback: Lookback period for swing point detection
            volume_threshold: Volume multiplier for breakout confirmation
            timeframe: Trading timeframe
        """
        super().__init__(name="LONG_Bullish_Divergence", timeframe=timeframe)
        self.rsi = RSI(period=rsi_period)
        self.swing_detector = SwingPointDetector(lookback=swing_lookback)
        self.volume_threshold = volume_threshold
        self.min_candles = max(rsi_period, swing_lookback) + 10

    def analyze(self, candles: List[Candle]) -> Optional[TradingSignal]:
        """
        Analyze candles for bullish divergence entry setup.

        Args:
            candles: List of Candle objects

        Returns:
            TradingSignal if conditions met, None otherwise
        """
        if not self.is_ready() or len(candles) < self.min_candles:
            return None

        # Update indicators
        self.rsi.update(candles)
        self.swing_detector.calculate(candles)

        current_candle = candles[-1]
        current_price = current_candle.close

        # 1. Check for bullish divergence (price lower low, RSI higher low)
        has_divergence, div_strength = self._check_bullish_divergence(candles)
        if not has_divergence:
            return None

        # 2. Check volume decreasing on retracement
        volume_decreasing = self._check_volume_decreasing(candles)

        # 3. Check for local resistance breakout
        resistance_break = self._check_resistance_breakout(candles)
        if not resistance_break:
            return None

        # 4. Check for expansive volume on breakout
        volume_expansion = self._check_volume_expansion(candles)

        # Calculate strength score
        strength_score = 0
        reasons = []

        if has_divergence:
            strength_score += div_strength
            reasons.append(f"Bullish RSI divergence detected (strength: {div_strength})")

        if volume_decreasing:
            strength_score += 15
            reasons.append("Volume decreasing on retracement (healthy pullback)")

        if resistance_break:
            strength_score += 25
            reasons.append("Local resistance broken to upside")

        if volume_expansion:
            strength_score += 20
            reasons.append(f"Expansive volume on breakout ({volume_expansion:.1f}x average)")

        # Check if RSI is not overbought
        rsi_value = self.rsi.current_value
        if rsi_value and rsi_value < 70:
            strength_score += 10
            reasons.append(f"RSI not overbought ({rsi_value:.1f})")

        # Calculate stop loss and take profit
        swing_low = self._get_recent_swing_low(candles)
        stop_loss = swing_low * 0.995  # Below swing low with buffer
        risk = current_price - stop_loss

        # Ensure risk is reasonable (max 3% from entry)
        if risk / current_price > 0.03:
            return None

        take_profit = current_price + (risk * 2.0)  # 2:1 R/R

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
                'rsi': rsi_value,
                'swing_low': swing_low,
                'current_volume': current_candle.volume,
                'avg_volume': self._get_average_volume(candles, 20),
                'divergence_strength': div_strength,
            },
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=2.0
        )

        self.add_signal(signal)
        return signal

    def _check_bullish_divergence(self, candles: List[Candle]) -> tuple[bool, int]:
        """
        Check for bullish divergence (price lower low, RSI higher low).

        Returns:
            Tuple of (has_divergence, strength_score)
        """
        if not self.rsi.is_ready() or len(candles) < 20:
            return False, 0

        # Get recent swing lows
        swing_lows = []
        rsi_at_lows = []

        for i in range(len(candles) - 5, max(len(candles) - 50, 0), -1):
            # Check if this is a swing low
            if i < 5 or i >= len(candles) - 2:
                continue

            is_swing_low = all(
                candles[i].low <= candles[j].low
                for j in range(max(0, i - 3), min(len(candles), i + 4))
                if j != i
            )

            if is_swing_low:
                swing_lows.append((i, candles[i].low))

                # Get RSI value at this swing low
                # Approximate RSI by recalculating for this point
                temp_rsi = RSI(period=self.rsi.period)
                temp_rsi.update(candles[:i + 1])
                if temp_rsi.current_value:
                    rsi_at_lows.append((i, temp_rsi.current_value))

        # Need at least 2 swing lows to compare
        if len(swing_lows) < 2 or len(rsi_at_lows) < 2:
            return False, 0

        # Check last two swing lows
        prev_low_idx, prev_low_price = swing_lows[-2]
        curr_low_idx, curr_low_price = swing_lows[-1]

        # Find corresponding RSI values
        prev_rsi = next((rsi for idx, rsi in rsi_at_lows if idx == prev_low_idx), None)
        curr_rsi = next((rsi for idx, rsi in rsi_at_lows if idx == curr_low_idx), None)

        if prev_rsi is None or curr_rsi is None:
            return False, 0

        # Bullish divergence: price makes lower low, RSI makes higher low
        price_lower_low = curr_low_price < prev_low_price
        rsi_higher_low = curr_rsi > prev_rsi

        if price_lower_low and rsi_higher_low:
            # Calculate divergence strength
            price_diff = abs(curr_low_price - prev_low_price) / prev_low_price
            rsi_diff = abs(curr_rsi - prev_rsi)

            # Stronger divergence = higher score
            strength = min(40, int(20 + (price_diff * 100) + (rsi_diff / 2)))

            return True, strength

        return False, 0

    def _check_volume_decreasing(self, candles: List[Candle], lookback: int = 10) -> bool:
        """
        Check if volume is decreasing on retracement.

        Args:
            candles: List of candles
            lookback: Number of candles to check

        Returns:
            True if volume trend is decreasing
        """
        if len(candles) < lookback:
            return False

        recent_candles = candles[-lookback:]
        volumes = [c.volume for c in recent_candles]

        # Check if volume is generally trending down
        first_half_avg = sum(volumes[:lookback // 2]) / (lookback // 2)
        second_half_avg = sum(volumes[lookback // 2:]) / (lookback - lookback // 2)

        return second_half_avg < first_half_avg * 0.8  # 20% decrease

    def _check_resistance_breakout(self, candles: List[Candle], lookback: int = 20) -> bool:
        """
        Check if price broke local resistance.

        Args:
            candles: List of candles
            lookback: Lookback period

        Returns:
            True if resistance broken
        """
        if len(candles) < lookback + 1:
            return False

        current_price = candles[-1].close
        recent_candles = candles[-lookback - 1:-1]  # Exclude current candle

        # Find local resistance (recent swing high)
        resistance = max(c.high for c in recent_candles)

        # Current price should be above resistance
        return current_price > resistance

    def _check_volume_expansion(self, candles: List[Candle], lookback: int = 20) -> float:
        """
        Check for expansive volume on breakout.

        Args:
            candles: List of candles
            lookback: Lookback for average volume

        Returns:
            Volume expansion ratio (0.0 if no expansion)
        """
        if len(candles) < lookback:
            return 0.0

        current_volume = candles[-1].volume
        avg_volume = self._get_average_volume(candles, lookback)

        if avg_volume == 0:
            return 0.0

        expansion_ratio = current_volume / avg_volume

        # Return ratio if above threshold, else 0
        return expansion_ratio if expansion_ratio >= self.volume_threshold else 0.0

    def _get_average_volume(self, candles: List[Candle], period: int) -> float:
        """Get average volume over period."""
        if len(candles) < period:
            period = len(candles)

        recent_volumes = [c.volume for c in candles[-period:]]
        return sum(recent_volumes) / len(recent_volumes) if recent_volumes else 0.0

    def _get_recent_swing_low(self, candles: List[Candle], lookback: int = 20) -> float:
        """Get the most recent swing low."""
        if len(candles) < lookback:
            lookback = len(candles)

        recent_candles = candles[-lookback:]
        return min(c.low for c in recent_candles)

    def is_ready(self) -> bool:
        """Check if strategy has enough data."""
        return self.rsi.is_ready()
