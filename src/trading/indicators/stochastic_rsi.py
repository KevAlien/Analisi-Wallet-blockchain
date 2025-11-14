"""
Stochastic RSI indicator.

Formula:
Stoch RSI = (RSI - RSI Low) / (RSI High - RSI Low)
With smoothing:
%K = SMA(Stoch RSI, smooth_k)
%D = SMA(%K, smooth_d)
"""
from typing import List, Optional
from .base_indicator import BaseIndicator, Candle
from .rsi import RSI


class StochasticRSI(BaseIndicator):
    """Stochastic RSI indicator."""

    def __init__(self, rsi_period: int = 14, stoch_period: int = 14,
                 smooth_k: int = 3, smooth_d: int = 3):
        """
        Initialize Stochastic RSI indicator.

        Args:
            rsi_period: Period for RSI calculation (default: 14)
            stoch_period: Lookback period for stochastic calculation (default: 14)
            smooth_k: Smoothing period for %K line (default: 3)
            smooth_d: Smoothing period for %D line (default: 3)
        """
        super().__init__(stoch_period)
        self.rsi = RSI(rsi_period)
        self.stoch_period = stoch_period
        self.smooth_k = smooth_k
        self.smooth_d = smooth_d

        self.stoch_rsi_values: List[float] = []
        self.k_values: List[float] = []
        self.d_values: List[float] = []

    def calculate(self, candles: List[Candle]) -> Optional[float]:
        """
        Calculate Stochastic RSI value.

        Args:
            candles: List of Candle objects

        Returns:
            Current Stochastic RSI %K value or None if insufficient data
        """
        # Update RSI first
        rsi_value = self.rsi.update(candles)

        if rsi_value is None or len(self.rsi.values) < self.stoch_period:
            return None

        # Get recent RSI values
        recent_rsi = self.rsi.values[-self.stoch_period:]

        # Calculate Stochastic RSI
        rsi_low = min(recent_rsi)
        rsi_high = max(recent_rsi)

        # Avoid division by zero
        if rsi_high - rsi_low == 0:
            stoch_rsi = 50.0  # Neutral value when no movement
        else:
            stoch_rsi = ((rsi_value - rsi_low) / (rsi_high - rsi_low)) * 100

        self.stoch_rsi_values.append(stoch_rsi)

        # Calculate %K (smoothed Stochastic RSI)
        if len(self.stoch_rsi_values) >= self.smooth_k:
            k_value = sum(self.stoch_rsi_values[-self.smooth_k:]) / self.smooth_k
            self.k_values.append(k_value)
        else:
            return None

        # Calculate %D (smoothed %K)
        if len(self.k_values) >= self.smooth_d:
            d_value = sum(self.k_values[-self.smooth_d:]) / self.smooth_d
            self.d_values.append(d_value)
        else:
            return None

        return k_value

    @property
    def k(self) -> Optional[float]:
        """Get current %K value."""
        return self.k_values[-1] if self.k_values else None

    @property
    def d(self) -> Optional[float]:
        """Get current %D value."""
        return self.d_values[-1] if self.d_values else None

    @property
    def previous_k(self) -> Optional[float]:
        """Get previous %K value."""
        return self.k_values[-2] if len(self.k_values) >= 2 else None

    @property
    def previous_d(self) -> Optional[float]:
        """Get previous %D value."""
        return self.d_values[-2] if len(self.d_values) >= 2 else None

    def is_oversold(self, threshold: float = 20.0) -> bool:
        """
        Check if Stochastic RSI indicates oversold condition.

        Args:
            threshold: Threshold below which is considered oversold (default: 20)

        Returns:
            True if oversold
        """
        return self.k is not None and self.k < threshold

    def is_overbought(self, threshold: float = 80.0) -> bool:
        """
        Check if Stochastic RSI indicates overbought condition.

        Args:
            threshold: Threshold above which is considered overbought (default: 80)

        Returns:
            True if overbought
        """
        return self.k is not None and self.k > threshold

    def k_cross_above_d(self) -> bool:
        """
        Check if %K line crossed above %D line (bullish signal).

        Returns:
            True if bullish crossover occurred
        """
        if self.k is None or self.d is None:
            return False
        if self.previous_k is None or self.previous_d is None:
            return False

        # Current: K above D
        # Previous: K below or equal D
        current_above = self.k > self.d
        previous_below_or_equal = self.previous_k <= self.previous_d

        return current_above and previous_below_or_equal

    def k_cross_below_d(self) -> bool:
        """
        Check if %K line crossed below %D line (bearish signal).

        Returns:
            True if bearish crossover occurred
        """
        if self.k is None or self.d is None:
            return False
        if self.previous_k is None or self.previous_d is None:
            return False

        # Current: K below D
        # Previous: K above or equal D
        current_below = self.k < self.d
        previous_above_or_equal = self.previous_k >= self.previous_d

        return current_below and previous_above_or_equal

    def bullish_crossover_in_oversold(self, oversold_threshold: float = 20.0) -> bool:
        """
        Detect bullish crossover in oversold zone (strong buy signal).

        Args:
            oversold_threshold: Oversold threshold (default: 20)

        Returns:
            True if bullish crossover in oversold zone
        """
        return self.k_cross_above_d() and self.k < oversold_threshold

    def bearish_crossover_in_overbought(self, overbought_threshold: float = 80.0) -> bool:
        """
        Detect bearish crossover in overbought zone (strong sell signal).

        Args:
            overbought_threshold: Overbought threshold (default: 80)

        Returns:
            True if bearish crossover in overbought zone
        """
        return self.k_cross_below_d() and self.k > overbought_threshold

    def is_ready(self) -> bool:
        """Check if indicator has enough data to be reliable."""
        return (len(self.k_values) >= self.smooth_k and
                len(self.d_values) >= self.smooth_d and
                self.rsi.is_ready())

    def reset(self):
        """Reset Stochastic RSI to initial state."""
        super().reset()
        self.rsi.reset()
        self.stoch_rsi_values = []
        self.k_values = []
        self.d_values = []
