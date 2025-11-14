"""
EMA Crossover Strategy with Heikin Ashi confirmation.

Entry Conditions (LONG):
1. Fast EMA crosses above Slow EMA (crossover positive)
2. Candle closes completely above the crossover point
3. Heikin Ashi turns green
4. Next HA green candle exceeds previous one
5. Price must be at least above Fibonacci 0.236 level from swing high (optional)

Parameters:
- For higher timeframes: EMA 20, 50, 100, 200
- For day trading: EMA 8, 14, 50

Exit Conditions:
- Opposite crossover
- Price breaks below EMA 200
- Stop loss: above maximum of candle before breakout (adjusted for volatility)
"""
from typing import List, Optional
from .base_strategy import BaseStrategy, TradingSignal, SignalType, SignalStrength
from ..indicators import Candle, EMA, MultiEMA, HeikinAshi


class EMACrossoverStrategy(BaseStrategy):
    """EMA Crossover strategy with Heikin Ashi confirmation."""

    def __init__(self, fast_period: int = 20, slow_period: int = 50,
                 trend_period: int = 200, timeframe: str = "1h"):
        """
        Initialize EMA Crossover strategy.

        Args:
            fast_period: Fast EMA period (default: 20)
            slow_period: Slow EMA period (default: 50)
            trend_period: Trend EMA period (default: 200)
            timeframe: Trading timeframe (default: "1h")
        """
        super().__init__(name="EMA Crossover", timeframe=timeframe)

        self.fast_period = fast_period
        self.slow_period = slow_period
        self.trend_period = trend_period

        # Initialize indicators
        self.ema_fast = EMA(fast_period)
        self.ema_slow = EMA(slow_period)
        self.ema_trend = EMA(trend_period)
        self.heikin_ashi = HeikinAshi()

        # Track position state
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
        if not self.is_ready() or not candles:
            return None

        # Update all indicators
        self.ema_fast.update(candles)
        self.ema_slow.update(candles)
        self.ema_trend.update(candles)
        ha_candles = self.heikin_ashi.transform(candles)

        current_candle = candles[-1]
        current_price = current_candle.close

        # Check for LONG entry
        if not self.in_position:
            long_signal = self._check_long_entry(candles, ha_candles, current_price)
            if long_signal:
                self.in_position = True
                self.position_type = SignalType.LONG
                self.add_signal(long_signal)
                return long_signal

            # Check for SHORT entry
            short_signal = self._check_short_entry(candles, ha_candles, current_price)
            if short_signal:
                self.in_position = True
                self.position_type = SignalType.SHORT
                self.add_signal(short_signal)
                return short_signal

        # Check for exit conditions
        else:
            exit_signal = self._check_exit(candles, current_price)
            if exit_signal:
                self.in_position = False
                self.position_type = None
                self.add_signal(exit_signal)
                return exit_signal

        return None

    def _check_long_entry(self, candles: List[Candle], ha_candles: List,
                         current_price: float) -> Optional[TradingSignal]:
        """
        Check for LONG entry conditions.

        Returns:
            TradingSignal if LONG conditions met, None otherwise
        """
        reasons = []
        strength_score = 0

        # 1. Fast EMA crosses above Slow EMA
        if not self.ema_fast.cross_above(self.ema_slow):
            return None

        reasons.append(f"EMA {self.fast_period} crossed above EMA {self.slow_period}")
        strength_score += 1

        # 2. Candle closes above crossover point
        crossover_level = self.ema_fast.current_value
        if current_price <= crossover_level:
            return None

        reasons.append(f"Price ({current_price:.2f}) closed above crossover ({crossover_level:.2f})")
        strength_score += 1

        # 3. Heikin Ashi turns green
        latest_ha = self.heikin_ashi.get_latest()
        if not latest_ha or not latest_ha.is_green:
            return None

        reasons.append("Heikin Ashi turned green (bullish)")
        strength_score += 1

        # 4. Next HA green candle exceeds previous
        if self.heikin_ashi.green_candle_exceeds_previous():
            reasons.append("HA green candle exceeds previous (momentum confirmed)")
            strength_score += 2

        # 5. Price above trend EMA (additional confirmation)
        if self.ema_trend.current_value and current_price > self.ema_trend.current_value:
            reasons.append(f"Price above EMA {self.trend_period} (strong uptrend)")
            strength_score += 2

        # Calculate stop loss and take profit
        stop_loss = self.calculate_stop_loss(current_price, SignalType.LONG, candles)
        risk_reward = 2.0 if strength_score >= 4 else 1.5
        take_profit = self.calculate_take_profit(current_price, stop_loss, risk_reward)

        # Determine signal strength
        if strength_score >= 5:
            strength = SignalStrength.VERY_STRONG
        elif strength_score >= 4:
            strength = SignalStrength.STRONG
        elif strength_score >= 3:
            strength = SignalStrength.MEDIUM
        else:
            strength = SignalStrength.WEAK

        return TradingSignal(
            signal_type=SignalType.LONG,
            strength=strength,
            price=current_price,
            timestamp=candles[-1].timestamp,
            strategy_name=self.name,
            reasons=reasons,
            indicators={
                f'EMA_{self.fast_period}': self.ema_fast.current_value,
                f'EMA_{self.slow_period}': self.ema_slow.current_value,
                f'EMA_{self.trend_period}': self.ema_trend.current_value,
                'HA_color': 'green',
                'HA_body_size': latest_ha.body_size if latest_ha else None,
            },
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=risk_reward
        )

    def _check_short_entry(self, candles: List[Candle], ha_candles: List,
                          current_price: float) -> Optional[TradingSignal]:
        """
        Check for SHORT entry conditions (opposite of LONG).

        Returns:
            TradingSignal if SHORT conditions met, None otherwise
        """
        reasons = []
        strength_score = 0

        # 1. Fast EMA crosses below Slow EMA
        if not self.ema_fast.cross_below(self.ema_slow):
            return None

        reasons.append(f"EMA {self.fast_period} crossed below EMA {self.slow_period}")
        strength_score += 1

        # 2. Candle closes below crossover point
        crossover_level = self.ema_fast.current_value
        if current_price >= crossover_level:
            return None

        reasons.append(f"Price ({current_price:.2f}) closed below crossover ({crossover_level:.2f})")
        strength_score += 1

        # 3. Heikin Ashi turns red
        latest_ha = self.heikin_ashi.get_latest()
        if not latest_ha or not latest_ha.is_red:
            return None

        reasons.append("Heikin Ashi turned red (bearish)")
        strength_score += 1

        # 4. Consecutive red HA candles
        if self.heikin_ashi.consecutive_red_candles(2):
            reasons.append("Consecutive HA red candles (momentum confirmed)")
            strength_score += 2

        # 5. Price below trend EMA (additional confirmation)
        if self.ema_trend.current_value and current_price < self.ema_trend.current_value:
            reasons.append(f"Price below EMA {self.trend_period} (strong downtrend)")
            strength_score += 2

        # Calculate stop loss and take profit
        stop_loss = self.calculate_stop_loss(current_price, SignalType.SHORT, candles)
        risk_reward = 2.0 if strength_score >= 4 else 1.5
        take_profit = self.calculate_take_profit(current_price, stop_loss, risk_reward)

        # Determine signal strength
        if strength_score >= 5:
            strength = SignalStrength.VERY_STRONG
        elif strength_score >= 4:
            strength = SignalStrength.STRONG
        elif strength_score >= 3:
            strength = SignalStrength.MEDIUM
        else:
            strength = SignalStrength.WEAK

        return TradingSignal(
            signal_type=SignalType.SHORT,
            strength=strength,
            price=current_price,
            timestamp=candles[-1].timestamp,
            strategy_name=self.name,
            reasons=reasons,
            indicators={
                f'EMA_{self.fast_period}': self.ema_fast.current_value,
                f'EMA_{self.slow_period}': self.ema_slow.current_value,
                f'EMA_{self.trend_period}': self.ema_trend.current_value,
                'HA_color': 'red',
                'HA_body_size': latest_ha.body_size if latest_ha else None,
            },
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=risk_reward
        )

    def _check_exit(self, candles: List[Candle], current_price: float) -> Optional[TradingSignal]:
        """
        Check for exit conditions.

        Returns:
            TradingSignal for exit if conditions met, None otherwise
        """
        if not self.position_type:
            return None

        reasons = []

        # Exit LONG position
        if self.position_type == SignalType.LONG:
            # Exit if fast EMA crosses below slow EMA
            if self.ema_fast.cross_below(self.ema_slow):
                reasons.append("EMA bearish crossover - exit LONG")

            # Exit if price breaks below trend EMA
            elif self.ema_trend.current_value and current_price < self.ema_trend.current_value:
                reasons.append(f"Price broke below EMA {self.trend_period} - exit LONG")

            # Exit if HA turns bearish
            elif self.heikin_ashi.trend_changed_to_bearish():
                reasons.append("Heikin Ashi turned bearish - exit LONG")

            if reasons:
                return TradingSignal(
                    signal_type=SignalType.EXIT_LONG,
                    strength=SignalStrength.STRONG,
                    price=current_price,
                    timestamp=candles[-1].timestamp,
                    strategy_name=self.name,
                    reasons=reasons,
                    indicators={
                        f'EMA_{self.fast_period}': self.ema_fast.current_value,
                        f'EMA_{self.slow_period}': self.ema_slow.current_value,
                        f'EMA_{self.trend_period}': self.ema_trend.current_value,
                    }
                )

        # Exit SHORT position
        elif self.position_type == SignalType.SHORT:
            # Exit if fast EMA crosses above slow EMA
            if self.ema_fast.cross_above(self.ema_slow):
                reasons.append("EMA bullish crossover - exit SHORT")

            # Exit if price breaks above trend EMA
            elif self.ema_trend.current_value and current_price > self.ema_trend.current_value:
                reasons.append(f"Price broke above EMA {self.trend_period} - exit SHORT")

            # Exit if HA turns bullish
            elif self.heikin_ashi.trend_changed_to_bullish():
                reasons.append("Heikin Ashi turned bullish - exit SHORT")

            if reasons:
                return TradingSignal(
                    signal_type=SignalType.EXIT_SHORT,
                    strength=SignalStrength.STRONG,
                    price=current_price,
                    timestamp=candles[-1].timestamp,
                    strategy_name=self.name,
                    reasons=reasons,
                    indicators={
                        f'EMA_{self.fast_period}': self.ema_fast.current_value,
                        f'EMA_{self.slow_period}': self.ema_slow.current_value,
                        f'EMA_{self.trend_period}': self.ema_trend.current_value,
                    }
                )

        return None

    def is_ready(self) -> bool:
        """Check if strategy has enough data to generate signals."""
        return (self.ema_fast.is_ready() and
                self.ema_slow.is_ready() and
                self.ema_trend.is_ready() and
                len(self.heikin_ashi.ha_candles) >= 2)

    def reset(self):
        """Reset strategy to initial state."""
        super().reset()
        self.ema_fast.reset()
        self.ema_slow.reset()
        self.ema_trend.reset()
        self.heikin_ashi.reset()
        self.in_position = False
        self.position_type = None
