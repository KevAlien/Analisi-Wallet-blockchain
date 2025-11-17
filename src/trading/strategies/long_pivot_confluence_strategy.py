"""
LONG Entry Strategy 4: Pivot Point + Triple Confluence.

Entry conditions:
1. Price at S1 or S2 (standard pivot)
2. Stochastic RSI bullish crossover (K above D, below 20)
3. VWAP broken to the upside
4. Entry: micro resistance breakout, next candle confirmation
"""
from typing import List, Optional
from .base_strategy import BaseStrategy, TradingSignal, SignalType, SignalStrength
from ..indicators import Candle
from ..indicators.pivot_points import PivotPoints
from ..indicators.stochastic_rsi import StochasticRSI
from ..indicators.vwap import VWAP


class LongPivotConfluenceStrategy(BaseStrategy):
    """
    LONG Entry Strategy 4: Pivot Point + Triple Confluence.

    Optimal for:
    - High probability reversal at pivot support
    - Multiple indicator confirmation
    """

    def __init__(
        self,
        stoch_rsi_period: int = 14,
        vwap_reset_daily: bool = True,
        oversold_threshold: float = 20.0,
        timeframe: str = "1h"
    ):
        """
        Initialize Pivot Confluence LONG strategy.

        Args:
            stoch_rsi_period: Stochastic RSI period
            vwap_reset_daily: Reset VWAP daily
            oversold_threshold: Stochastic RSI oversold level
            timeframe: Trading timeframe
        """
        super().__init__(name="LONG_Pivot_Confluence", timeframe=timeframe)
        self.pivot_points = PivotPoints(reset_daily=True)
        self.stoch_rsi = StochasticRSI(rsi_period=stoch_rsi_period)
        self.vwap = VWAP()
        self.oversold_threshold = oversold_threshold
        self.min_candles = 50

    def analyze(self, candles: List[Candle]) -> Optional[TradingSignal]:
        """
        Analyze candles for pivot confluence entry setup.

        Args:
            candles: List of Candle objects

        Returns:
            TradingSignal if conditions met, None otherwise
        """
        if not self.is_ready() or len(candles) < self.min_candles:
            return None

        # Update indicators
        self.pivot_points.calculate(candles)
        self.stoch_rsi.calculate(candles)
        self.vwap.update(candles)

        current_candle = candles[-1]
        current_price = current_candle.close

        pivot_levels = self.pivot_points.get_levels()
        if not pivot_levels:
            return None

        # 1. Check if price at S1 or S2 pivot support
        at_pivot_support = self._check_pivot_support(current_price, pivot_levels)
        if not at_pivot_support:
            return None

        # 2. Check for Stochastic RSI bullish crossover in oversold
        stoch_crossover = self._check_stoch_rsi_crossover()

        # 3. Check for VWAP breakout to upside
        vwap_breakout = self._check_vwap_breakout(candles)

        # 4. Check for micro resistance breakout
        micro_break = self._check_micro_resistance_break(candles)
        if not micro_break:
            return None

        # Calculate strength score
        strength_score = 0
        reasons = []

        if at_pivot_support:
            strength_score += 25
            pivot_level = at_pivot_support
            reasons.append(f"Price at pivot support level: {pivot_level}")

        if stoch_crossover:
            strength_score += 30
            k_val = self.stoch_rsi.k
            reasons.append(f"Stochastic RSI bullish crossover in oversold (K: {k_val:.1f})")

        if vwap_breakout:
            strength_score += 25
            reasons.append("VWAP broken to the upside (bullish momentum)")

        if micro_break:
            strength_score += 20
            reasons.append("Micro resistance broken (entry confirmation)")

        # Calculate stop loss and take profit
        # Use pivot support as stop loss level
        pivot_price = getattr(pivot_levels, at_pivot_support.lower())
        stop_loss = pivot_price * 0.995  # Below pivot support
        risk = current_price - stop_loss

        # Ensure risk is reasonable (max 3% from entry)
        if risk / current_price > 0.03:
            return None

        # For pivot bounces, use next resistance as target
        next_resistance = self._get_next_resistance(current_price, pivot_levels)
        if next_resistance:
            take_profit = min(next_resistance, current_price + (risk * 3.0))
        else:
            take_profit = current_price + (risk * 2.0)

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
                'pivot_point': pivot_levels.pp,
                'support_1': pivot_levels.s1,
                'support_2': pivot_levels.s2,
                'resistance_1': pivot_levels.r1,
                'stoch_rsi_k': self.stoch_rsi.k,
                'stoch_rsi_d': self.stoch_rsi.d,
                'vwap': self.vwap.current_value,
            },
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=(take_profit - current_price) / risk if risk > 0 else 2.0
        )

        self.add_signal(signal)
        return signal

    def _check_pivot_support(self, price: float, pivot_levels, tolerance: float = 0.01) -> Optional[str]:
        """
        Check if price is at S1 or S2 pivot support.

        Args:
            price: Current price
            pivot_levels: PivotLevels object
            tolerance: Price tolerance

        Returns:
            Support level name if at support, None otherwise
        """
        # Check S1
        if abs(price - pivot_levels.s1) <= pivot_levels.s1 * tolerance:
            return 'S1'

        # Check S2
        if abs(price - pivot_levels.s2) <= pivot_levels.s2 * tolerance:
            return 'S2'

        return None

    def _check_stoch_rsi_crossover(self) -> bool:
        """
        Check for bullish Stochastic RSI crossover in oversold zone.

        Returns:
            True if bullish crossover in oversold
        """
        if not self.stoch_rsi.is_ready():
            return False

        # Check if K crossed above D
        crossover = self.stoch_rsi.k_cross_above_d()

        # Check if in oversold zone
        in_oversold = self.stoch_rsi.k and self.stoch_rsi.k < self.oversold_threshold

        return crossover and in_oversold

    def _check_vwap_breakout(self, candles: List[Candle]) -> bool:
        """
        Check if price broke VWAP to the upside.

        Args:
            candles: List of candles

        Returns:
            True if VWAP broken upward
        """
        if len(candles) < 2:
            return False

        vwap_val = self.vwap.current_value
        if vwap_val is None:
            return False

        current_price = candles[-1].close
        prev_price = candles[-2].close

        # Previous candle below VWAP, current above
        return prev_price <= vwap_val and current_price > vwap_val

    def _check_micro_resistance_break(self, candles: List[Candle], lookback: int = 5) -> bool:
        """
        Check for micro resistance breakout (recent local high).

        Args:
            candles: List of candles
            lookback: Lookback for micro resistance

        Returns:
            True if micro resistance broken
        """
        if len(candles) < lookback + 1:
            return False

        current_price = candles[-1].close
        recent_candles = candles[-lookback - 1:-1]

        # Find micro resistance (recent high)
        micro_resistance = max(c.high for c in recent_candles)

        # Current price above micro resistance
        return current_price > micro_resistance

    def _get_next_resistance(self, price: float, pivot_levels) -> Optional[float]:
        """
        Get next resistance level above current price.

        Args:
            price: Current price
            pivot_levels: PivotLevels object

        Returns:
            Next resistance price or None
        """
        return pivot_levels.get_nearest_resistance(price)

    def is_ready(self) -> bool:
        """Check if strategy has enough data."""
        return (self.stoch_rsi.is_ready() and
                self.vwap.current_value is not None and
                self.pivot_points.get_levels() is not None)
