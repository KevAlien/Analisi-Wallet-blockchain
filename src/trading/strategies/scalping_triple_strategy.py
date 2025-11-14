"""
Scalping Triple Indicator Strategy.

This is defined as one of the best strategies for crypto scalping.

Indicators:
1. Pivot Points (Standard)
2. Stochastic RSI
3. VWAP

Entry Conditions LONG (all must occur, order not relevant):
1. Bullish Stochastic RSI crossover (K crosses D from below)
2. VWAP broken to the upside
3. Support established on Pivot Point OR resistance broken
4. Entry confirmation: next candle above current

Entry Conditions SHORT: Exact opposite

Optimal Timeframe: 5-30 minutes
"""
from typing import List, Optional
from .base_strategy import BaseStrategy, TradingSignal, SignalType, SignalStrength
from ..indicators import Candle, StochasticRSI, VWAP, PivotPoints


class ScalpingTripleStrategy(BaseStrategy):
    """Scalping strategy using Pivot Points, Stochastic RSI, and VWAP."""

    def __init__(self, timeframe: str = "15m"):
        """
        Initialize Scalping Triple Indicator strategy.

        Args:
            timeframe: Trading timeframe (default: "15m", optimal: 5-30min)
        """
        super().__init__(name="Scalping Triple Indicator", timeframe=timeframe)

        # Initialize indicators
        self.stoch_rsi = StochasticRSI(rsi_period=14, stoch_period=14, smooth_k=3, smooth_d=3)
        self.vwap = VWAP(reset_daily=True)
        self.pivot_points = PivotPoints(reset_daily=True)

        # Track state
        self.stoch_crossover_detected = False
        self.vwap_breakout_detected = False
        self.pivot_condition_met = False
        self.in_position = False
        self.position_type: Optional[SignalType] = None

    def analyze(self, candles: List[Candle]) -> Optional[TradingSignal]:
        """
        Analyze candles and generate trading signal.

        Args:
            candles: List of Candle objects

        Returns:
            TradingSignal if all conditions are met, None otherwise
        """
        if not self.is_ready() or len(candles) < 3:
            return None

        # Update all indicators
        self.stoch_rsi.calculate(candles)
        self.vwap.update(candles)
        self.pivot_points.calculate(candles)

        current_candle = candles[-1]
        previous_candle = candles[-2]
        current_price = current_candle.close

        # Check for entry signals
        if not self.in_position:
            # Check for LONG entry
            long_signal = self._check_long_entry(candles, current_price)
            if long_signal:
                self.in_position = True
                self.position_type = SignalType.LONG
                self._reset_conditions()
                self.add_signal(long_signal)
                return long_signal

            # Check for SHORT entry
            short_signal = self._check_short_entry(candles, current_price)
            if short_signal:
                self.in_position = True
                self.position_type = SignalType.SHORT
                self._reset_conditions()
                self.add_signal(short_signal)
                return short_signal

        # Check for exit
        else:
            exit_signal = self._check_exit(candles, current_price)
            if exit_signal:
                self.in_position = False
                self.position_type = None
                self.add_signal(exit_signal)
                return exit_signal

        return None

    def _check_long_entry(self, candles: List[Candle], current_price: float) -> Optional[TradingSignal]:
        """
        Check for LONG entry - all conditions must be met (order not relevant).

        Returns:
            TradingSignal if all conditions met, None otherwise
        """
        reasons = []
        conditions_met = 0
        total_conditions = 3  # Core conditions

        # Condition 1: Bullish Stochastic RSI crossover (K crosses D from below)
        if self.stoch_rsi.k_cross_above_d():
            self.stoch_crossover_detected = True
            reasons.append(f"Stoch RSI bullish crossover (K={self.stoch_rsi.k:.1f} > D={self.stoch_rsi.d:.1f})")
            conditions_met += 1
        elif self.stoch_crossover_detected:
            # Keep condition active for a few candles
            conditions_met += 1

        # Condition 2: VWAP broken to the upside
        if self.vwap.price_crossed_above(candles):
            self.vwap_breakout_detected = True
            reasons.append(f"Price broke above VWAP ({self.vwap.current_value:.2f})")
            conditions_met += 1
        elif self.vwap_breakout_detected and current_price > self.vwap.current_value:
            # Keep condition active if still above VWAP
            conditions_met += 1

        # Condition 3: Support on Pivot Point OR Resistance broken
        pivot_levels = self.pivot_points.get_levels()
        if pivot_levels:
            # Check if support established
            if pivot_levels.is_at_support(current_price, tolerance=0.003):
                reasons.append(f"Support established on Pivot Point")
                self.pivot_condition_met = True
                conditions_met += 1

            # OR check if resistance broken
            elif self.pivot_points.resistance_broken(candles):
                nearest_resistance = pivot_levels.get_nearest_resistance(candles[-2].close)
                reasons.append(f"Pivot resistance broken (R={nearest_resistance:.2f})")
                self.pivot_condition_met = True
                conditions_met += 1

            # Keep condition if already met
            elif self.pivot_condition_met:
                conditions_met += 1

        # All 3 conditions must be met
        if conditions_met < total_conditions:
            return None

        # Additional confirmation: next candle above current (we use current > previous as proxy)
        if current_price <= candles[-2].close:
            return None

        reasons.append("Confirmation: candle closed above previous")

        # Additional strength indicators
        strength_score = conditions_met

        # Bonus: Stoch RSI in oversold zone (strong signal)
        if self.stoch_rsi.k and self.stoch_rsi.k < 30:
            reasons.append("Stoch RSI in oversold zone (very bullish)")
            strength_score += 2

        # Bonus: Price significantly above VWAP
        if self.vwap.current_value:
            distance = self.vwap.get_distance_from_vwap(current_price)
            if distance and 0 < distance < 1:  # 0-1% above
                reasons.append(f"Price {distance:.2f}% above VWAP (optimal entry)")
                strength_score += 1

        # Calculate stop loss and take profit (tight for scalping)
        stop_loss = self.calculate_stop_loss(current_price, SignalType.LONG, candles, atr_multiplier=1.0)
        risk_reward = 2.0  # Scalping typically uses 2:1 R:R
        take_profit = self.calculate_take_profit(current_price, stop_loss, risk_reward)

        # Determine signal strength
        if strength_score >= 6:
            strength = SignalStrength.VERY_STRONG
        elif strength_score >= 5:
            strength = SignalStrength.STRONG
        elif strength_score >= 4:
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
                'Stoch_K': self.stoch_rsi.k,
                'Stoch_D': self.stoch_rsi.d,
                'VWAP': self.vwap.current_value,
                'Pivot_Levels': self.pivot_points.get_support_resistance_map(),
            },
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=risk_reward
        )

    def _check_short_entry(self, candles: List[Candle], current_price: float) -> Optional[TradingSignal]:
        """
        Check for SHORT entry - exact opposite of LONG conditions.

        Returns:
            TradingSignal if all conditions met, None otherwise
        """
        reasons = []
        conditions_met = 0
        total_conditions = 3

        # Condition 1: Bearish Stochastic RSI crossover (K crosses D from above)
        if self.stoch_rsi.k_cross_below_d():
            self.stoch_crossover_detected = True
            reasons.append(f"Stoch RSI bearish crossover (K={self.stoch_rsi.k:.1f} < D={self.stoch_rsi.d:.1f})")
            conditions_met += 1
        elif self.stoch_crossover_detected:
            conditions_met += 1

        # Condition 2: VWAP broken to the downside
        if self.vwap.price_crossed_below(candles):
            self.vwap_breakout_detected = True
            reasons.append(f"Price broke below VWAP ({self.vwap.current_value:.2f})")
            conditions_met += 1
        elif self.vwap_breakout_detected and current_price < self.vwap.current_value:
            conditions_met += 1

        # Condition 3: Resistance on Pivot Point OR Support broken
        pivot_levels = self.pivot_points.get_levels()
        if pivot_levels:
            # Check if resistance established
            if pivot_levels.is_at_resistance(current_price, tolerance=0.003):
                reasons.append(f"Resistance established on Pivot Point")
                self.pivot_condition_met = True
                conditions_met += 1

            # OR check if support broken
            elif self.pivot_points.support_broken(candles):
                nearest_support = pivot_levels.get_nearest_support(candles[-2].close)
                reasons.append(f"Pivot support broken (S={nearest_support:.2f})")
                self.pivot_condition_met = True
                conditions_met += 1

            elif self.pivot_condition_met:
                conditions_met += 1

        # All 3 conditions must be met
        if conditions_met < total_conditions:
            return None

        # Additional confirmation: next candle below current
        if current_price >= candles[-2].close:
            return None

        reasons.append("Confirmation: candle closed below previous")

        # Additional strength indicators
        strength_score = conditions_met

        # Bonus: Stoch RSI in overbought zone (strong signal)
        if self.stoch_rsi.k and self.stoch_rsi.k > 70:
            reasons.append("Stoch RSI in overbought zone (very bearish)")
            strength_score += 2

        # Bonus: Price significantly below VWAP
        if self.vwap.current_value:
            distance = self.vwap.get_distance_from_vwap(current_price)
            if distance and -1 < distance < 0:  # 0-1% below
                reasons.append(f"Price {abs(distance):.2f}% below VWAP (optimal entry)")
                strength_score += 1

        # Calculate stop loss and take profit (tight for scalping)
        stop_loss = self.calculate_stop_loss(current_price, SignalType.SHORT, candles, atr_multiplier=1.0)
        risk_reward = 2.0
        take_profit = self.calculate_take_profit(current_price, stop_loss, risk_reward)

        # Determine signal strength
        if strength_score >= 6:
            strength = SignalStrength.VERY_STRONG
        elif strength_score >= 5:
            strength = SignalStrength.STRONG
        elif strength_score >= 4:
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
                'Stoch_K': self.stoch_rsi.k,
                'Stoch_D': self.stoch_rsi.d,
                'VWAP': self.vwap.current_value,
                'Pivot_Levels': self.pivot_points.get_support_resistance_map(),
            },
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=risk_reward
        )

    def _check_exit(self, candles: List[Candle], current_price: float) -> Optional[TradingSignal]:
        """Check for exit conditions (scalping - quick exits)."""
        if not self.position_type:
            return None

        reasons = []

        if self.position_type == SignalType.LONG:
            # Exit on opposite Stoch RSI crossover
            if self.stoch_rsi.k_cross_below_d():
                reasons.append("Stoch RSI bearish crossover - exit LONG")

            # Exit if price crosses below VWAP
            elif self.vwap.price_crossed_below(candles):
                reasons.append("Price crossed below VWAP - exit LONG")

            # Exit if Stoch RSI overbought
            elif self.stoch_rsi.is_overbought(threshold=80):
                reasons.append("Stoch RSI overbought - take profit")

            if reasons:
                return TradingSignal(
                    signal_type=SignalType.EXIT_LONG,
                    strength=SignalStrength.STRONG,
                    price=current_price,
                    timestamp=candles[-1].timestamp,
                    strategy_name=self.name,
                    reasons=reasons,
                    indicators={
                        'Stoch_K': self.stoch_rsi.k,
                        'Stoch_D': self.stoch_rsi.d,
                        'VWAP': self.vwap.current_value,
                    }
                )

        elif self.position_type == SignalType.SHORT:
            # Exit on opposite Stoch RSI crossover
            if self.stoch_rsi.k_cross_above_d():
                reasons.append("Stoch RSI bullish crossover - exit SHORT")

            # Exit if price crosses above VWAP
            elif self.vwap.price_crossed_above(candles):
                reasons.append("Price crossed above VWAP - exit SHORT")

            # Exit if Stoch RSI oversold
            elif self.stoch_rsi.is_oversold(threshold=20):
                reasons.append("Stoch RSI oversold - take profit")

            if reasons:
                return TradingSignal(
                    signal_type=SignalType.EXIT_SHORT,
                    strength=SignalStrength.STRONG,
                    price=current_price,
                    timestamp=candles[-1].timestamp,
                    strategy_name=self.name,
                    reasons=reasons,
                    indicators={
                        'Stoch_K': self.stoch_rsi.k,
                        'Stoch_D': self.stoch_rsi.d,
                        'VWAP': self.vwap.current_value,
                    }
                )

        return None

    def _reset_conditions(self):
        """Reset condition tracking flags."""
        self.stoch_crossover_detected = False
        self.vwap_breakout_detected = False
        self.pivot_condition_met = False

    def is_ready(self) -> bool:
        """Check if all indicators have enough data."""
        return (self.stoch_rsi.is_ready() and
                self.vwap.current_value is not None and
                self.pivot_points.get_levels() is not None)

    def reset(self):
        """Reset strategy state."""
        super().reset()
        self.stoch_rsi.reset()
        self.vwap.reset()
        self.pivot_points.reset()
        self._reset_conditions()
        self.in_position = False
        self.position_type = None
