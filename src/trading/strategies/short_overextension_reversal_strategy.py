"""
SHORT Entry Strategy 5: Overextension + Reversal Candles.

Entry conditions:
1. Price >3 standard deviations above moving average
2. RSI >70 persistent (4H/Daily)
3. Candle pattern: shooting star, bearish engulfing, dark cloud cover
4. Entry: break of reversal candle low
"""
from typing import List, Optional
from .base_strategy import BaseStrategy, TradingSignal, SignalType, SignalStrength
from ..indicators import Candle
from ..indicators.standard_deviation import StandardDeviation
from ..indicators.rsi import RSI
from ..indicators.candlestick_patterns import CandlestickPatterns
from ..indicators.ema import EMA


class ShortOverextensionReversalStrategy(BaseStrategy):
    """
    SHORT Entry Strategy 5: Overextension + Reversal Candles.

    Optimal for:
    - Extreme overextension reversals
    - High probability mean reversion trades
    """

    def __init__(
        self,
        ma_period: int = 20,
        std_dev_threshold: float = 3.0,  # 3 standard deviations
        rsi_period: int = 14,
        rsi_overbought: float = 70.0,
        timeframe: str = "4h"
    ):
        """
        Initialize Overextension Reversal SHORT strategy.

        Args:
            ma_period: Moving average period
            std_dev_threshold: Standard deviation threshold
            rsi_period: RSI period
            rsi_overbought: RSI overbought level
            timeframe: Trading timeframe
        """
        super().__init__(name="SHORT_Overextension_Reversal", timeframe=timeframe)
        self.ema = EMA(period=ma_period)
        self.std_dev = StandardDeviation(period=ma_period, num_std=std_dev_threshold)
        self.rsi = RSI(period=rsi_period)
        self.candle_patterns = CandlestickPatterns()
        self.std_dev_threshold = std_dev_threshold
        self.rsi_overbought = rsi_overbought
        self.min_candles = max(ma_period, rsi_period) + 10

    def analyze(self, candles: List[Candle]) -> Optional[TradingSignal]:
        """
        Analyze candles for overextension reversal entry setup.

        Args:
            candles: List of Candle objects

        Returns:
            TradingSignal if conditions met, None otherwise
        """
        if not self.is_ready() or len(candles) < self.min_candles:
            return None

        # Update indicators
        self.ema.update(candles)
        self.std_dev.calculate(candles)
        self.rsi.update(candles)
        self.candle_patterns.calculate(candles)

        current_candle = candles[-1]
        current_price = current_candle.close
        ema_value = self.ema.current_value
        rsi_value = self.rsi.current_value

        if not all([ema_value, rsi_value]):
            return None

        # 1. Check if price overextended (>3 std dev above MA)
        overextended = self.std_dev.is_overextended_above(current_price, self.std_dev_threshold)
        if not overextended:
            return None

        # 2. Check if RSI persistently overbought
        rsi_persistent = self._check_persistent_overbought(candles)

        # 3. Check for bearish reversal candle pattern
        reversal_pattern = self._check_reversal_patterns()
        if not reversal_pattern:
            return None

        # 4. Check if reversal candle low was broken
        reversal_break = self._check_reversal_candle_break(candles)
        if not reversal_break:
            return None

        # Calculate strength score
        strength_score = 0
        reasons = []

        if overextended:
            num_std = self.std_dev.get_num_std_from_mean(current_price)
            strength_score += 35
            reasons.append(f"Price overextended ({num_std:.1f} std dev above MA)")

        if rsi_persistent:
            strength_score += 25
            reasons.append(f"RSI persistently overbought ({rsi_value:.1f})")

        if reversal_pattern:
            patterns = self.candle_patterns.get_patterns()
            strength_score += 25
            reasons.append(f"Bearish reversal pattern: {', '.join(patterns)}")

        if reversal_break:
            strength_score += 15
            reasons.append("Reversal candle low broken (entry confirmation)")

        # Calculate stop loss and take profit
        # Stop above reversal candle high
        reversal_candle = self._get_reversal_candle(candles)
        if reversal_candle:
            stop_loss = reversal_candle.high * 1.01
        else:
            stop_loss = current_price * 1.03  # 3% stop

        risk = stop_loss - current_price

        # Ensure risk is reasonable (max 3% from entry)
        if risk / current_price > 0.03:
            stop_loss = current_price * 1.03
            risk = stop_loss - current_price

        # For overextension, target is mean reversion (back to MA)
        if ema_value:
            take_profit = max(ema_value, current_price - (risk * 2.0))
        else:
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
                'ema': ema_value,
                'rsi': rsi_value,
                'std_dev_above': self.std_dev.get_num_std_from_mean(current_price),
                'upper_band': self.std_dev.upper_band,
                'reversal_patterns': self.candle_patterns.get_patterns(),
            },
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=(current_price - take_profit) / risk if risk > 0 else 2.0
        )

        self.add_signal(signal)
        return signal

    def _check_persistent_overbought(self, candles: List[Candle], lookback: int = 5) -> bool:
        """
        Check if RSI has been persistently overbought.

        Args:
            candles: List of candles
            lookback: Number of candles to check

        Returns:
            True if RSI persistently above threshold
        """
        if len(candles) < lookback:
            return False

        # Check recent candles
        overbought_count = 0
        for i in range(1, lookback + 1):
            temp_rsi = RSI(period=self.rsi.period)
            temp_rsi.update(candles[:-i] if i > 1 else candles)

            if temp_rsi.current_value and temp_rsi.current_value > self.rsi_overbought:
                overbought_count += 1

        # At least 3 out of last 5 candles overbought
        return overbought_count >= 3

    def _check_reversal_patterns(self) -> bool:
        """Check for bearish reversal candlestick patterns."""
        if not self.candle_patterns.detected_patterns:
            return False

        # Check for bearish patterns
        bearish_patterns = {
            'shooting_star',
            'bearish_engulfing',
            'dark_cloud_cover',
            'evening_star'
        }

        return bool(bearish_patterns & set(self.candle_patterns.detected_patterns))

    def _check_reversal_candle_break(self, candles: List[Candle]) -> bool:
        """
        Check if reversal candle low was broken.

        Args:
            candles: List of candles

        Returns:
            True if reversal candle low broken
        """
        if len(candles) < 2:
            return False

        reversal_candle = self._get_reversal_candle(candles)
        if not reversal_candle:
            return False

        current_candle = candles[-1]

        # Current candle should break below reversal candle low
        return current_candle.close < reversal_candle.low

    def _get_reversal_candle(self, candles: List[Candle]) -> Optional[Candle]:
        """
        Get the reversal candle from recent candles.

        Returns:
            Reversal candle or None
        """
        if len(candles) < 2:
            return None

        # Check last 3 candles for reversal pattern
        for i in range(min(3, len(candles))):
            idx = -(i + 2)  # Start from -2 (previous candle)
            if abs(idx) > len(candles):
                continue

            candle = candles[idx]

            # Check if this candle has a reversal pattern
            if self.candle_patterns.is_shooting_star(candle):
                return candle

            # Check for engulfing (needs previous candle)
            if abs(idx) + 1 <= len(candles):
                prev = candles[idx - 1]
                if self.candle_patterns.is_bearish_engulfing(prev, candle):
                    return candle

        # Default to previous candle
        return candles[-2]

    def is_ready(self) -> bool:
        """Check if strategy has enough data."""
        return (self.ema.is_ready() and
                self.std_dev.is_ready() and
                self.rsi.is_ready())
