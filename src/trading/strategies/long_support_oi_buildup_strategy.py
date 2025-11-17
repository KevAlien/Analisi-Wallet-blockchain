"""
LONG Entry Strategy 3: Key Support + Long Buildup (OI).

Entry conditions:
1. Level tested 2-3 times on higher timeframe
2. Open Interest increasing + stable price/slight uptrend
3. Volume profile: high volume at support
4. Entry: intraday resistance breakout with OI confirmation
"""
from typing import List, Optional
from .base_strategy import BaseStrategy, TradingSignal, SignalType, SignalStrength
from ..indicators import Candle
from ..indicators.volume_profile import VolumeProfile


class LongSupportOIBuildupStrategy(BaseStrategy):
    """
    LONG Entry Strategy 3: Key Support + Long Buildup (OI).

    Optimal for:
    - Breakout from accumulation zones
    - High volume support level bounces
    """

    def __init__(
        self,
        volume_profile_lookback: int = 100,
        min_touches: int = 2,
        oi_increase_threshold: float = 1.1,  # 10% OI increase
        timeframe: str = "1h"
    ):
        """
        Initialize Support + OI Buildup LONG strategy.

        Args:
            volume_profile_lookback: Lookback for volume profile calculation
            min_touches: Minimum number of support touches required
            oi_increase_threshold: Minimum OI increase ratio
            timeframe: Trading timeframe
        """
        super().__init__(name="LONG_Support_OI_Buildup", timeframe=timeframe)
        self.volume_profile = VolumeProfile(lookback=volume_profile_lookback)
        self.min_touches = min_touches
        self.oi_increase_threshold = oi_increase_threshold
        self.min_candles = volume_profile_lookback + 10

        # Track Open Interest (if available)
        self.oi_history: List[float] = []

    def analyze(self, candles: List[Candle], open_interest: Optional[List[float]] = None) -> Optional[TradingSignal]:
        """
        Analyze candles for support + OI buildup entry setup.

        Args:
            candles: List of Candle objects
            open_interest: Optional list of Open Interest values (parallel to candles)

        Returns:
            TradingSignal if conditions met, None otherwise
        """
        if not self.is_ready() or len(candles) < self.min_candles:
            return None

        # Update indicators
        self.volume_profile.calculate(candles)

        # Track OI if provided
        if open_interest:
            self.oi_history = open_interest[-50:]  # Keep last 50

        current_candle = candles[-1]
        current_price = current_candle.close

        # 1. Find key support level (high volume node)
        support_level = self._find_key_support(current_price)
        if support_level is None:
            return None

        # 2. Check if level tested multiple times
        multi_touch = self.volume_profile.is_multi_touch_level(
            support_level,
            candles[-50:] if len(candles) >= 50 else candles,
            min_touches=self.min_touches
        )
        if not multi_touch:
            return None

        # 3. Check Open Interest increasing (if available)
        oi_increasing = self._check_oi_increasing() if self.oi_history else True

        # 4. Check price stable or slight uptrend
        price_stable = self._check_price_stable(candles)

        # 5. Check for intraday resistance breakout
        resistance_break = self._check_resistance_breakout(candles)
        if not resistance_break:
            return None

        # Calculate strength score
        strength_score = 0
        reasons = []

        if multi_touch:
            strength_score += 30
            reasons.append(f"Key support tested {self.min_touches}+ times at {support_level:.2f}")

        if self.volume_profile.is_high_volume_level(support_level):
            strength_score += 25
            reasons.append("High volume support zone (accumulation)")

        if oi_increasing:
            strength_score += 20
            if self.oi_history:
                reasons.append(f"Open Interest increasing (LONG buildup)")
            else:
                reasons.append("OI data not available (neutral)")

        if price_stable:
            strength_score += 15
            reasons.append("Price consolidating near support (stable/slight uptrend)")

        if resistance_break:
            strength_score += 10
            reasons.append("Intraday resistance broken (breakout confirmation)")

        # Calculate stop loss and take profit
        stop_loss = support_level * 0.98  # Below support with buffer
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
                'support_level': support_level,
                'point_of_control': self.volume_profile.point_of_control,
                'current_oi': self.oi_history[-1] if self.oi_history else None,
                'oi_change': self._get_oi_change() if self.oi_history else None,
                'multi_touch_level': multi_touch,
            },
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=2.0
        )

        self.add_signal(signal)
        return signal

    def _find_key_support(self, current_price: float) -> Optional[float]:
        """
        Find nearest key support level based on volume profile.

        Args:
            current_price: Current price

        Returns:
            Support level price or None
        """
        # Get high volume nodes below current price
        supports = self.volume_profile.get_support_levels(current_price, count=3)

        if not supports:
            return None

        # Return closest support
        return supports[0]

    def _check_oi_increasing(self, lookback: int = 10) -> bool:
        """
        Check if Open Interest is increasing (LONG buildup).

        Args:
            lookback: Number of periods to check

        Returns:
            True if OI is trending up
        """
        if len(self.oi_history) < lookback:
            return False

        recent_oi = self.oi_history[-lookback:]

        # Compare first half vs second half
        first_half_avg = sum(recent_oi[:lookback // 2]) / (lookback // 2)
        second_half_avg = sum(recent_oi[lookback // 2:]) / (lookback - lookback // 2)

        # OI should be increasing
        return second_half_avg >= first_half_avg * self.oi_increase_threshold

    def _get_oi_change(self) -> Optional[float]:
        """Get percentage change in OI."""
        if len(self.oi_history) < 2:
            return None

        old_oi = self.oi_history[-10] if len(self.oi_history) >= 10 else self.oi_history[0]
        current_oi = self.oi_history[-1]

        if old_oi == 0:
            return None

        return ((current_oi - old_oi) / old_oi) * 100

    def _check_price_stable(self, candles: List[Candle], lookback: int = 20) -> bool:
        """
        Check if price is stable or in slight uptrend.

        Args:
            candles: List of candles
            lookback: Lookback period

        Returns:
            True if price is consolidating
        """
        if len(candles) < lookback:
            return False

        recent_candles = candles[-lookback:]
        closes = [c.close for c in recent_candles]

        # Check price range
        price_high = max(closes)
        price_low = min(closes)
        price_range = (price_high - price_low) / price_low

        # Stable if range is less than 5%
        stable = price_range < 0.05

        # Check if slightly up trending
        first_half_avg = sum(closes[:lookback // 2]) / (lookback // 2)
        second_half_avg = sum(closes[lookback // 2:]) / (lookback - lookback // 2)

        slightly_up = second_half_avg >= first_half_avg * 0.99  # Not down

        return stable and slightly_up

    def _check_resistance_breakout(self, candles: List[Candle], lookback: int = 10) -> bool:
        """
        Check for intraday resistance breakout.

        Args:
            candles: List of candles
            lookback: Lookback period

        Returns:
            True if resistance broken
        """
        if len(candles) < lookback + 1:
            return False

        current_price = candles[-1].close
        recent_candles = candles[-lookback - 1:-1]

        # Find intraday resistance
        resistance = max(c.high for c in recent_candles)

        # Current price above resistance
        return current_price > resistance

    def is_ready(self) -> bool:
        """Check if strategy has enough data."""
        return self.volume_profile.values != [] and len(self.volume_profile.values) > 0
