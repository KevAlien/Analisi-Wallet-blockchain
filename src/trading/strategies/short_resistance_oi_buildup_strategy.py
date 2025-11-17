"""
SHORT Entry Strategy 3: Key Resistance + Short Buildup (OI).

Entry conditions:
1. Multi-touch resistance level on higher timeframe
2. OI increasing + price decreasing = short buildup
3. Volume spike on rejection
4. Entry: intraday support break with decreasing OI confirmation
"""
from typing import List, Optional
from .base_strategy import BaseStrategy, TradingSignal, SignalType, SignalStrength
from ..indicators import Candle
from ..indicators.volume_profile import VolumeProfile


class ShortResistanceOIBuildupStrategy(BaseStrategy):
    """
    SHORT Entry Strategy 3: Key Resistance + Short Buildup (OI).

    Optimal for:
    - Breakdown from distribution zones
    - High volume resistance level rejections
    """

    def __init__(
        self,
        volume_profile_lookback: int = 100,
        min_touches: int = 2,
        oi_increase_threshold: float = 1.1,  # 10% OI increase
        volume_spike_threshold: float = 1.5,  # 1.5x average volume
        timeframe: str = "1h"
    ):
        """
        Initialize Resistance + OI Buildup SHORT strategy.

        Args:
            volume_profile_lookback: Lookback for volume profile
            min_touches: Minimum resistance touches required
            oi_increase_threshold: Minimum OI increase ratio
            volume_spike_threshold: Volume spike multiplier
            timeframe: Trading timeframe
        """
        super().__init__(name="SHORT_Resistance_OI_Buildup", timeframe=timeframe)
        self.volume_profile = VolumeProfile(lookback=volume_profile_lookback)
        self.min_touches = min_touches
        self.oi_increase_threshold = oi_increase_threshold
        self.volume_spike_threshold = volume_spike_threshold
        self.min_candles = volume_profile_lookback + 10

        # Track Open Interest
        self.oi_history: List[float] = []

    def analyze(self, candles: List[Candle], open_interest: Optional[List[float]] = None) -> Optional[TradingSignal]:
        """
        Analyze candles for resistance + OI buildup entry setup.

        Args:
            candles: List of Candle objects
            open_interest: Optional list of Open Interest values

        Returns:
            TradingSignal if conditions met, None otherwise
        """
        if not self.is_ready() or len(candles) < self.min_candles:
            return None

        # Update indicators
        self.volume_profile.calculate(candles)

        # Track OI if provided
        if open_interest:
            self.oi_history = open_interest[-50:]

        current_candle = candles[-1]
        current_price = current_candle.close

        # 1. Find key resistance level
        resistance_level = self._find_key_resistance(current_price)
        if resistance_level is None:
            return None

        # 2. Check if level tested multiple times
        multi_touch = self.volume_profile.is_multi_touch_level(
            resistance_level,
            candles[-50:] if len(candles) >= 50 else candles,
            min_touches=self.min_touches
        )
        if not multi_touch:
            return None

        # 3. Check OI increasing + price decreasing (SHORT buildup)
        oi_short_buildup = self._check_oi_short_buildup(candles) if self.oi_history else True

        # 4. Check volume spike on rejection
        volume_spike = self._check_volume_spike(candles)

        # 5. Check for intraday support break
        support_break = self._check_support_breakdown(candles)
        if not support_break:
            return None

        # Calculate strength score
        strength_score = 0
        reasons = []

        if multi_touch:
            strength_score += 30
            reasons.append(f"Key resistance tested {self.min_touches}+ times at {resistance_level:.2f}")

        if self.volume_profile.is_high_volume_level(resistance_level):
            strength_score += 25
            reasons.append("High volume resistance zone (distribution)")

        if oi_short_buildup:
            strength_score += 20
            if self.oi_history:
                reasons.append("OI increasing + price down (SHORT buildup)")
            else:
                reasons.append("OI data not available (neutral)")

        if volume_spike:
            strength_score += 15
            reasons.append(f"Volume spike on rejection ({volume_spike:.1f}x average)")

        if support_break:
            strength_score += 10
            reasons.append("Intraday support broken (breakdown confirmation)")

        # Calculate stop loss and take profit
        stop_loss = resistance_level * 1.02  # Above resistance with buffer
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
                'resistance_level': resistance_level,
                'point_of_control': self.volume_profile.point_of_control,
                'current_oi': self.oi_history[-1] if self.oi_history else None,
                'oi_change': self._get_oi_change() if self.oi_history else None,
                'volume_spike': volume_spike if volume_spike else 0.0,
            },
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=2.0
        )

        self.add_signal(signal)
        return signal

    def _find_key_resistance(self, current_price: float) -> Optional[float]:
        """Find nearest key resistance level based on volume profile."""
        # Get high volume nodes above current price
        resistances = self.volume_profile.get_resistance_levels(current_price, count=3)

        if not resistances:
            return None

        # Return closest resistance
        return resistances[0]

    def _check_oi_short_buildup(self, candles: List[Candle], lookback: int = 10) -> bool:
        """
        Check if OI is increasing while price is decreasing (SHORT buildup).

        Args:
            candles: List of candles
            lookback: Lookback period

        Returns:
            True if SHORT buildup detected
        """
        if len(self.oi_history) < lookback or len(candles) < lookback:
            return False

        recent_oi = self.oi_history[-lookback:]
        recent_candles = candles[-lookback:]

        # Check if OI increasing
        first_half_oi = sum(recent_oi[:lookback // 2]) / (lookback // 2)
        second_half_oi = sum(recent_oi[lookback // 2:]) / (lookback - lookback // 2)
        oi_increasing = second_half_oi >= first_half_oi * self.oi_increase_threshold

        # Check if price decreasing
        first_half_prices = [c.close for c in recent_candles[:lookback // 2]]
        second_half_prices = [c.close for c in recent_candles[lookback // 2:]]
        first_avg = sum(first_half_prices) / len(first_half_prices)
        second_avg = sum(second_half_prices) / len(second_half_prices)
        price_decreasing = second_avg < first_avg

        return oi_increasing and price_decreasing

    def _get_oi_change(self) -> Optional[float]:
        """Get percentage change in OI."""
        if len(self.oi_history) < 2:
            return None

        old_oi = self.oi_history[-10] if len(self.oi_history) >= 10 else self.oi_history[0]
        current_oi = self.oi_history[-1]

        if old_oi == 0:
            return None

        return ((current_oi - old_oi) / old_oi) * 100

    def _check_volume_spike(self, candles: List[Candle], lookback: int = 20) -> float:
        """
        Check for volume spike on rejection.

        Args:
            candles: List of candles
            lookback: Lookback for average volume

        Returns:
            Volume spike ratio (0.0 if no spike)
        """
        if len(candles) < lookback + 1:
            return 0.0

        # Get average volume
        avg_candles = candles[-lookback - 1:-1]
        avg_volume = sum(c.volume for c in avg_candles) / len(avg_candles)

        if avg_volume == 0:
            return 0.0

        # Check recent candles for spike
        recent_candles = candles[-3:]
        max_recent_volume = max(c.volume for c in recent_candles)

        spike_ratio = max_recent_volume / avg_volume

        return spike_ratio if spike_ratio >= self.volume_spike_threshold else 0.0

    def _check_support_breakdown(self, candles: List[Candle], lookback: int = 10) -> bool:
        """Check for intraday support breakdown."""
        if len(candles) < lookback + 1:
            return False

        current_price = candles[-1].close
        recent_candles = candles[-lookback - 1:-1]

        # Find intraday support
        support = min(c.low for c in recent_candles)

        # Current price below support
        return current_price < support

    def is_ready(self) -> bool:
        """Check if strategy has enough data."""
        return self.volume_profile.values != [] and len(self.volume_profile.values) > 0
