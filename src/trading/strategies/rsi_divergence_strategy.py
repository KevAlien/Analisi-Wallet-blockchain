"""
RSI Divergence Day Trading Strategy.

Entry Conditions (LONG):
1. RSI forms Higher Low
2. Price forms Lower Low (bullish divergence)
3. Volume is decreasing during retracement
4. VWAP broken to the upside
5. VWAP support established
6. Entry on breakout of resistance

Timeframe: 5-15 minutes optimal
"""
from typing import List, Optional
from .base_strategy import BaseStrategy, TradingSignal, SignalType, SignalStrength
from ..indicators import Candle, RSI, VWAP


class RSIDivergenceStrategy(BaseStrategy):
    """RSI Divergence strategy with VWAP confirmation."""

    def __init__(self, rsi_period: int = 14, divergence_lookback: int = 10,
                 timeframe: str = "15m"):
        """
        Initialize RSI Divergence strategy.

        Args:
            rsi_period: RSI calculation period (default: 14)
            divergence_lookback: Lookback period for divergence detection (default: 10)
            timeframe: Trading timeframe (default: "15m")
        """
        super().__init__(name="RSI Divergence", timeframe=timeframe)

        self.rsi_period = rsi_period
        self.divergence_lookback = divergence_lookback

        # Initialize indicators
        self.rsi = RSI(rsi_period)
        self.vwap = VWAP(reset_daily=True)

        # Track state
        self.bullish_divergence_detected = False
        self.bearish_divergence_detected = False
        self.last_resistance_level: Optional[float] = None
        self.last_support_level: Optional[float] = None
        self.in_position = False
        self.position_type: Optional[SignalType] = None

    def analyze(self, candles: List[Candle]) -> Optional[TradingSignal]:
        """
        Analyze candles and generate trading signal.

        Args:
            candles: List of Candle objects

        Returns:
            TradingSignal if conditions are met, None otherwise
        """
        if not self.is_ready() or len(candles) < self.divergence_lookback:
            return None

        # Update indicators
        self.rsi.update(candles)
        self.vwap.update(candles)

        current_candle = candles[-1]
        current_price = current_candle.close

        # Check for entry signals
        if not self.in_position:
            # Check for LONG entry
            long_signal = self._check_long_entry(candles, current_price)
            if long_signal:
                self.in_position = True
                self.position_type = SignalType.LONG
                self.add_signal(long_signal)
                return long_signal

            # Check for SHORT entry
            short_signal = self._check_short_entry(candles, current_price)
            if short_signal:
                self.in_position = True
                self.position_type = SignalType.SHORT
                self.add_signal(short_signal)
                return short_signal

        # Check for exit
        else:
            exit_signal = self._check_exit(candles, current_price)
            if exit_signal:
                self.in_position = False
                self.position_type = None
                self.bullish_divergence_detected = False
                self.bearish_divergence_detected = False
                self.add_signal(exit_signal)
                return exit_signal

        return None

    def _check_long_entry(self, candles: List[Candle], current_price: float) -> Optional[TradingSignal]:
        """
        Check for LONG entry based on bullish RSI divergence.

        Returns:
            TradingSignal if conditions met, None otherwise
        """
        reasons = []
        strength_score = 0

        # Get recent prices
        recent_prices = [c.close for c in candles[-self.divergence_lookback:]]

        # 1. Detect bullish divergence
        has_divergence = self.rsi.detect_bullish_divergence(
            recent_prices,
            lookback=self.divergence_lookback
        )

        if has_divergence:
            self.bullish_divergence_detected = True
            reasons.append("Bullish RSI divergence detected (price lower low, RSI higher low)")
            strength_score += 3
        elif not self.bullish_divergence_detected:
            return None  # No divergence, no entry

        # 2. Check volume decreasing (using candle volume as proxy)
        recent_candles = candles[-5:]
        if len(recent_candles) >= 2:
            volume_decreasing = recent_candles[-1].volume < recent_candles[-2].volume
            if volume_decreasing:
                reasons.append("Volume decreasing during retracement")
                strength_score += 1

        # 3. VWAP broken to upside
        if self.vwap.price_crossed_above(candles):
            reasons.append("Price broke above VWAP (bullish)")
            strength_score += 2
        elif current_price <= self.vwap.current_value:
            # Still below VWAP, wait for breakout
            return None

        # 4. VWAP support established
        if self.vwap.is_support_established(candles, touches=2):
            reasons.append("VWAP established as support")
            strength_score += 2

        # 5. Resistance breakout confirmation
        resistance = self._find_recent_resistance(candles)
        if resistance and current_price > resistance:
            reasons.append(f"Price broke resistance at {resistance:.2f}")
            strength_score += 2
            self.last_resistance_level = resistance

        # Calculate stop loss and take profit
        stop_loss = self.calculate_stop_loss(current_price, SignalType.LONG, candles, atr_multiplier=1.5)
        risk_reward = 2.5 if strength_score >= 7 else 2.0
        take_profit = self.calculate_take_profit(current_price, stop_loss, risk_reward)

        # Determine signal strength
        if strength_score >= 8:
            strength = SignalStrength.VERY_STRONG
        elif strength_score >= 6:
            strength = SignalStrength.STRONG
        elif strength_score >= 4:
            strength = SignalStrength.MEDIUM
        else:
            strength = SignalStrength.WEAK

        # Minimum strength required for entry
        if strength_score < 4:
            return None

        return TradingSignal(
            signal_type=SignalType.LONG,
            strength=strength,
            price=current_price,
            timestamp=candles[-1].timestamp,
            strategy_name=self.name,
            reasons=reasons,
            indicators={
                'RSI': self.rsi.current_value,
                'VWAP': self.vwap.current_value,
                'divergence_type': 'bullish',
                'resistance_broken': self.last_resistance_level,
            },
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=risk_reward
        )

    def _check_short_entry(self, candles: List[Candle], current_price: float) -> Optional[TradingSignal]:
        """
        Check for SHORT entry based on bearish RSI divergence.

        Returns:
            TradingSignal if conditions met, None otherwise
        """
        reasons = []
        strength_score = 0

        # Get recent prices
        recent_prices = [c.close for c in candles[-self.divergence_lookback:]]

        # 1. Detect bearish divergence
        has_divergence = self.rsi.detect_bearish_divergence(
            recent_prices,
            lookback=self.divergence_lookback
        )

        if has_divergence:
            self.bearish_divergence_detected = True
            reasons.append("Bearish RSI divergence detected (price higher high, RSI lower high)")
            strength_score += 3
        elif not self.bearish_divergence_detected:
            return None  # No divergence, no entry

        # 2. Check volume decreasing
        recent_candles = candles[-5:]
        if len(recent_candles) >= 2:
            volume_decreasing = recent_candles[-1].volume < recent_candles[-2].volume
            if volume_decreasing:
                reasons.append("Volume decreasing during rally")
                strength_score += 1

        # 3. VWAP broken to downside
        if self.vwap.price_crossed_below(candles):
            reasons.append("Price broke below VWAP (bearish)")
            strength_score += 2
        elif current_price >= self.vwap.current_value:
            # Still above VWAP, wait for breakdown
            return None

        # 4. VWAP resistance established
        if self.vwap.is_resistance_established(candles, touches=2):
            reasons.append("VWAP established as resistance")
            strength_score += 2

        # 5. Support breakdown confirmation
        support = self._find_recent_support(candles)
        if support and current_price < support:
            reasons.append(f"Price broke support at {support:.2f}")
            strength_score += 2
            self.last_support_level = support

        # Calculate stop loss and take profit
        stop_loss = self.calculate_stop_loss(current_price, SignalType.SHORT, candles, atr_multiplier=1.5)
        risk_reward = 2.5 if strength_score >= 7 else 2.0
        take_profit = self.calculate_take_profit(current_price, stop_loss, risk_reward)

        # Determine signal strength
        if strength_score >= 8:
            strength = SignalStrength.VERY_STRONG
        elif strength_score >= 6:
            strength = SignalStrength.STRONG
        elif strength_score >= 4:
            strength = SignalStrength.MEDIUM
        else:
            strength = SignalStrength.WEAK

        # Minimum strength required for entry
        if strength_score < 4:
            return None

        return TradingSignal(
            signal_type=SignalType.SHORT,
            strength=strength,
            price=current_price,
            timestamp=candles[-1].timestamp,
            strategy_name=self.name,
            reasons=reasons,
            indicators={
                'RSI': self.rsi.current_value,
                'VWAP': self.vwap.current_value,
                'divergence_type': 'bearish',
                'support_broken': self.last_support_level,
            },
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=risk_reward
        )

    def _check_exit(self, candles: List[Candle], current_price: float) -> Optional[TradingSignal]:
        """Check for exit conditions."""
        if not self.position_type:
            return None

        reasons = []

        if self.position_type == SignalType.LONG:
            # Exit on opposite divergence
            recent_prices = [c.close for c in candles[-self.divergence_lookback:]]
            if self.rsi.detect_bearish_divergence(recent_prices, lookback=self.divergence_lookback):
                reasons.append("Bearish divergence detected - exit LONG")

            # Exit if VWAP turns to resistance
            elif self.vwap.price_crossed_below(candles):
                reasons.append("Price broke below VWAP - exit LONG")

            # Exit if RSI overbought
            elif self.rsi.is_overbought(threshold=70):
                reasons.append("RSI overbought - exit LONG")

            if reasons:
                return TradingSignal(
                    signal_type=SignalType.EXIT_LONG,
                    strength=SignalStrength.STRONG,
                    price=current_price,
                    timestamp=candles[-1].timestamp,
                    strategy_name=self.name,
                    reasons=reasons,
                    indicators={'RSI': self.rsi.current_value, 'VWAP': self.vwap.current_value}
                )

        elif self.position_type == SignalType.SHORT:
            # Exit on opposite divergence
            recent_prices = [c.close for c in candles[-self.divergence_lookback:]]
            if self.rsi.detect_bullish_divergence(recent_prices, lookback=self.divergence_lookback):
                reasons.append("Bullish divergence detected - exit SHORT")

            # Exit if VWAP turns to support
            elif self.vwap.price_crossed_above(candles):
                reasons.append("Price broke above VWAP - exit SHORT")

            # Exit if RSI oversold
            elif self.rsi.is_oversold(threshold=30):
                reasons.append("RSI oversold - exit SHORT")

            if reasons:
                return TradingSignal(
                    signal_type=SignalType.EXIT_SHORT,
                    strength=SignalStrength.STRONG,
                    price=current_price,
                    timestamp=candles[-1].timestamp,
                    strategy_name=self.name,
                    reasons=reasons,
                    indicators={'RSI': self.rsi.current_value, 'VWAP': self.vwap.current_value}
                )

        return None

    def _find_recent_resistance(self, candles: List[Candle], lookback: int = 20) -> Optional[float]:
        """Find recent resistance level."""
        if len(candles) < lookback:
            return None

        recent = candles[-lookback:]
        highs = [c.high for c in recent]

        # Find significant high (swing high)
        for i in range(len(highs) - 3, 2, -1):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1]:
                return highs[i]

        return max(highs)

    def _find_recent_support(self, candles: List[Candle], lookback: int = 20) -> Optional[float]:
        """Find recent support level."""
        if len(candles) < lookback:
            return None

        recent = candles[-lookback:]
        lows = [c.low for c in recent]

        # Find significant low (swing low)
        for i in range(len(lows) - 3, 2, -1):
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1]:
                return lows[i]

        return min(lows)

    def is_ready(self) -> bool:
        """Check if strategy has enough data."""
        return self.rsi.is_ready() and self.vwap.current_value is not None

    def reset(self):
        """Reset strategy state."""
        super().reset()
        self.rsi.reset()
        self.vwap.reset()
        self.bullish_divergence_detected = False
        self.bearish_divergence_detected = False
        self.last_resistance_level = None
        self.last_support_level = None
        self.in_position = False
        self.position_type = None
