"""
Universal Divergence Detector Strategy.

Detects divergences between price and various oscillators (RSI, MACD, Stochastic, etc.)

Bullish Divergence (LONG):
- Price makes Lower Low
- Oscillator makes Higher Low
- Additional confirmations: Support break, Volume, EMA 200 support

Bearish Divergence (SHORT):
- Price makes Higher High
- Oscillator makes Lower High
- Additional confirmations: Resistance break, Volume, EMA 200 resistance

Exit:
- Opposite divergence
- EMA 200 break
- Stop loss hit
"""
from typing import List, Optional
from .base_strategy import BaseStrategy, TradingSignal, SignalType, SignalStrength
from ..indicators import Candle, RSI, EMA


class DivergenceDetectorStrategy(BaseStrategy):
    """Generic divergence detection strategy using RSI and price action."""

    def __init__(self, rsi_period: int = 14, ema_period: int = 200,
                 divergence_lookback: int = 10, timeframe: str = "1h"):
        """
        Initialize Divergence Detector strategy.

        Args:
            rsi_period: RSI calculation period (default: 14)
            ema_period: Trend EMA period (default: 200)
            divergence_lookback: Periods to look back for divergence (default: 10)
            timeframe: Trading timeframe (default: "1h")
        """
        super().__init__(name="Divergence Detector", timeframe=timeframe)

        self.rsi_period = rsi_period
        self.ema_period = ema_period
        self.divergence_lookback = divergence_lookback

        # Initialize indicators
        self.rsi = RSI(rsi_period)
        self.ema_trend = EMA(ema_period)

        # Track state
        self.in_position = False
        self.position_type: Optional[SignalType] = None
        self.last_divergence_type: Optional[str] = None

    def analyze(self, candles: List[Candle]) -> Optional[TradingSignal]:
        """
        Analyze candles for divergence patterns.

        Args:
            candles: List of Candle objects

        Returns:
            TradingSignal if divergence detected, None otherwise
        """
        if not self.is_ready() or len(candles) < self.divergence_lookback:
            return None

        # Update indicators
        self.rsi.update(candles)
        self.ema_trend.update(candles)

        current_candle = candles[-1]
        current_price = current_candle.close

        # Check for entry signals
        if not self.in_position:
            # Check for LONG entry (bullish divergence)
            long_signal = self._check_bullish_divergence(candles, current_price)
            if long_signal:
                self.in_position = True
                self.position_type = SignalType.LONG
                self.last_divergence_type = 'bullish'
                self.add_signal(long_signal)
                return long_signal

            # Check for SHORT entry (bearish divergence)
            short_signal = self._check_bearish_divergence(candles, current_price)
            if short_signal:
                self.in_position = True
                self.position_type = SignalType.SHORT
                self.last_divergence_type = 'bearish'
                self.add_signal(short_signal)
                return short_signal

        # Check for exit
        else:
            exit_signal = self._check_exit(candles, current_price)
            if exit_signal:
                self.in_position = False
                self.position_type = None
                self.last_divergence_type = None
                self.add_signal(exit_signal)
                return exit_signal

        return None

    def _check_bullish_divergence(self, candles: List[Candle], current_price: float) -> Optional[TradingSignal]:
        """
        Detect bullish divergence: Price LL, RSI HL.

        Returns:
            TradingSignal if bullish divergence confirmed, None otherwise
        """
        reasons = []
        strength_score = 0

        # Get recent data
        recent_prices = [c.close for c in candles[-self.divergence_lookback:]]

        # 1. Detect divergence using RSI
        has_divergence = self.rsi.detect_bullish_divergence(
            recent_prices,
            lookback=self.divergence_lookback
        )

        if not has_divergence:
            return None

        reasons.append("Bullish divergence: price Lower Low, RSI Higher Low")
        strength_score += 3

        # 2. Check RSI swing lows
        rsi_lows = self.rsi.get_swing_lows(lookback=self.divergence_lookback)
        if len(rsi_lows) >= 2:
            reasons.append(f"RSI swing lows detected: {len(rsi_lows)} points")
            strength_score += 1

        # 3. Price above EMA 200 (additional confirmation)
        if self.ema_trend.current_value and current_price > self.ema_trend.current_value:
            reasons.append(f"Price above EMA {self.ema_period} (strong support)")
            strength_score += 2

        # 4. RSI oversold (strong signal)
        if self.rsi.is_oversold(threshold=35):
            reasons.append(f"RSI oversold ({self.rsi.current_value:.1f}) - strong reversal potential")
            strength_score += 2

        # 5. Volume confirmation
        if len(candles) >= 3:
            recent_volume = [c.volume for c in candles[-3:]]
            if recent_volume[-1] > sum(recent_volume[:-1]) / 2:
                reasons.append("Volume increasing - strong buying interest")
                strength_score += 1

        # 6. Support level broken and reclaimed
        support = self._find_support(candles, lookback=20)
        if support and current_price > support:
            reasons.append(f"Price reclaimed support at {support:.2f}")
            strength_score += 1

        # Calculate stop loss and take profit
        stop_loss = self.calculate_stop_loss(current_price, SignalType.LONG, candles, atr_multiplier=2.0)
        risk_reward = 3.0 if strength_score >= 7 else 2.0
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

        # Minimum strength required
        if strength_score < 3:
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
                f'EMA_{self.ema_period}': self.ema_trend.current_value,
                'divergence_type': 'bullish',
                'rsi_swing_lows': rsi_lows,
            },
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=risk_reward
        )

    def _check_bearish_divergence(self, candles: List[Candle], current_price: float) -> Optional[TradingSignal]:
        """
        Detect bearish divergence: Price HH, RSI LH.

        Returns:
            TradingSignal if bearish divergence confirmed, None otherwise
        """
        reasons = []
        strength_score = 0

        # Get recent data
        recent_prices = [c.close for c in candles[-self.divergence_lookback:]]

        # 1. Detect divergence using RSI
        has_divergence = self.rsi.detect_bearish_divergence(
            recent_prices,
            lookback=self.divergence_lookback
        )

        if not has_divergence:
            return None

        reasons.append("Bearish divergence: price Higher High, RSI Lower High")
        strength_score += 3

        # 2. Check RSI swing highs
        rsi_highs = self.rsi.get_swing_highs(lookback=self.divergence_lookback)
        if len(rsi_highs) >= 2:
            reasons.append(f"RSI swing highs detected: {len(rsi_highs)} points")
            strength_score += 1

        # 3. Price below EMA 200 (additional confirmation)
        if self.ema_trend.current_value and current_price < self.ema_trend.current_value:
            reasons.append(f"Price below EMA {self.ema_period} (strong resistance)")
            strength_score += 2

        # 4. RSI overbought (strong signal)
        if self.rsi.is_overbought(threshold=65):
            reasons.append(f"RSI overbought ({self.rsi.current_value:.1f}) - strong reversal potential")
            strength_score += 2

        # 5. Volume confirmation
        if len(candles) >= 3:
            recent_volume = [c.volume for c in candles[-3:]]
            if recent_volume[-1] > sum(recent_volume[:-1]) / 2:
                reasons.append("Volume increasing - strong selling pressure")
                strength_score += 1

        # 6. Resistance level tested and rejected
        resistance = self._find_resistance(candles, lookback=20)
        if resistance and current_price < resistance:
            reasons.append(f"Price rejected at resistance {resistance:.2f}")
            strength_score += 1

        # Calculate stop loss and take profit
        stop_loss = self.calculate_stop_loss(current_price, SignalType.SHORT, candles, atr_multiplier=2.0)
        risk_reward = 3.0 if strength_score >= 7 else 2.0
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

        # Minimum strength required
        if strength_score < 3:
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
                f'EMA_{self.ema_period}': self.ema_trend.current_value,
                'divergence_type': 'bearish',
                'rsi_swing_highs': rsi_highs,
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
        recent_prices = [c.close for c in candles[-self.divergence_lookback:]]

        if self.position_type == SignalType.LONG:
            # Exit on opposite divergence
            if self.rsi.detect_bearish_divergence(recent_prices, lookback=self.divergence_lookback):
                reasons.append("Bearish divergence detected - exit LONG")

            # Exit if price breaks below EMA 200
            elif self.ema_trend.current_value and current_price < self.ema_trend.current_value:
                reasons.append(f"Price broke below EMA {self.ema_period} - exit LONG")

            # Exit if RSI extremely overbought
            elif self.rsi.is_overbought(threshold=75):
                reasons.append("RSI extremely overbought - take profit")

            if reasons:
                return TradingSignal(
                    signal_type=SignalType.EXIT_LONG,
                    strength=SignalStrength.STRONG,
                    price=current_price,
                    timestamp=candles[-1].timestamp,
                    strategy_name=self.name,
                    reasons=reasons,
                    indicators={
                        'RSI': self.rsi.current_value,
                        f'EMA_{self.ema_period}': self.ema_trend.current_value,
                    }
                )

        elif self.position_type == SignalType.SHORT:
            # Exit on opposite divergence
            if self.rsi.detect_bullish_divergence(recent_prices, lookback=self.divergence_lookback):
                reasons.append("Bullish divergence detected - exit SHORT")

            # Exit if price breaks above EMA 200
            elif self.ema_trend.current_value and current_price > self.ema_trend.current_value:
                reasons.append(f"Price broke above EMA {self.ema_period} - exit SHORT")

            # Exit if RSI extremely oversold
            elif self.rsi.is_oversold(threshold=25):
                reasons.append("RSI extremely oversold - take profit")

            if reasons:
                return TradingSignal(
                    signal_type=SignalType.EXIT_SHORT,
                    strength=SignalStrength.STRONG,
                    price=current_price,
                    timestamp=candles[-1].timestamp,
                    strategy_name=self.name,
                    reasons=reasons,
                    indicators={
                        'RSI': self.rsi.current_value,
                        f'EMA_{self.ema_period}': self.ema_trend.current_value,
                    }
                )

        return None

    def _find_support(self, candles: List[Candle], lookback: int = 20) -> Optional[float]:
        """Find recent support level."""
        if len(candles) < lookback:
            return None
        recent = candles[-lookback:]
        lows = [c.low for c in recent]
        return min(lows)

    def _find_resistance(self, candles: List[Candle], lookback: int = 20) -> Optional[float]:
        """Find recent resistance level."""
        if len(candles) < lookback:
            return None
        recent = candles[-lookback:]
        highs = [c.high for c in recent]
        return max(highs)

    def is_ready(self) -> bool:
        """Check if indicators have enough data."""
        return self.rsi.is_ready() and self.ema_trend.is_ready()

    def reset(self):
        """Reset strategy state."""
        super().reset()
        self.rsi.reset()
        self.ema_trend.reset()
        self.in_position = False
        self.position_type = None
        self.last_divergence_type = None
