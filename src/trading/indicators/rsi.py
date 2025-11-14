"""
Relative Strength Index (RSI) indicator.

Formula:
RS = Average Gain / Average Loss (over period 14)
RSI = 100 - (100 / (1 + RS))
"""
from typing import List, Optional
from .base_indicator import BaseIndicator, Candle


class RSI(BaseIndicator):
    """Relative Strength Index indicator."""

    def __init__(self, period: int = 14):
        """
        Initialize RSI indicator.

        Args:
            period: The lookback period for RSI calculation (default: 14)
        """
        super().__init__(period)
        self.gains: List[float] = []
        self.losses: List[float] = []
        self.avg_gain: Optional[float] = None
        self.avg_loss: Optional[float] = None

    def calculate(self, candles: List[Candle]) -> Optional[float]:
        """
        Calculate RSI value.

        Args:
            candles: List of Candle objects

        Returns:
            Current RSI value (0-100) or None if insufficient data
        """
        if len(candles) < self.period + 1:
            return None

        # Calculate price changes
        current_price = candles[-1].close
        previous_price = candles[-2].close
        change = current_price - previous_price

        gain = max(change, 0)
        loss = abs(min(change, 0))

        self.gains.append(gain)
        self.losses.append(loss)

        # Keep only last period values
        if len(self.gains) > self.period:
            self.gains.pop(0)
            self.losses.pop(0)

        # Calculate average gain and loss
        if len(self.gains) < self.period:
            return None

        if self.avg_gain is None or self.avg_loss is None:
            # First calculation: simple average
            self.avg_gain = sum(self.gains) / self.period
            self.avg_loss = sum(self.losses) / self.period
        else:
            # Smoothed average (Wilder's smoothing)
            self.avg_gain = ((self.avg_gain * (self.period - 1)) + gain) / self.period
            self.avg_loss = ((self.avg_loss * (self.period - 1)) + loss) / self.period

        # Avoid division by zero
        if self.avg_loss == 0:
            return 100.0

        # Calculate RS and RSI
        rs = self.avg_gain / self.avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def is_oversold(self, threshold: float = 30.0) -> bool:
        """
        Check if RSI indicates oversold condition.

        Args:
            threshold: RSI level below which is considered oversold (default: 30)

        Returns:
            True if RSI is oversold
        """
        return self.current_value is not None and self.current_value < threshold

    def is_overbought(self, threshold: float = 70.0) -> bool:
        """
        Check if RSI indicates overbought condition.

        Args:
            threshold: RSI level above which is considered overbought (default: 70)

        Returns:
            True if RSI is overbought
        """
        return self.current_value is not None and self.current_value > threshold

    def detect_bullish_divergence(self, prices: List[float], lookback: int = 5) -> bool:
        """
        Detect bullish divergence: price makes lower low, RSI makes higher low.

        Args:
            prices: Recent price data
            lookback: Number of periods to look back

        Returns:
            True if bullish divergence detected
        """
        if len(self.values) < lookback or len(prices) < lookback:
            return False

        recent_rsi = self.values[-lookback:]
        recent_prices = prices[-lookback:]

        # Find lows
        rsi_low_idx = recent_rsi.index(min(recent_rsi))
        price_low_idx = recent_prices.index(min(recent_prices))

        # Check if we have two distinct lows
        if rsi_low_idx == len(recent_rsi) - 1 or price_low_idx == len(recent_prices) - 1:
            return False

        # Price makes lower low
        price_lower_low = recent_prices[-1] < recent_prices[price_low_idx]

        # RSI makes higher low
        rsi_higher_low = recent_rsi[-1] > recent_rsi[rsi_low_idx]

        return price_lower_low and rsi_higher_low

    def detect_bearish_divergence(self, prices: List[float], lookback: int = 5) -> bool:
        """
        Detect bearish divergence: price makes higher high, RSI makes lower high.

        Args:
            prices: Recent price data
            lookback: Number of periods to look back

        Returns:
            True if bearish divergence detected
        """
        if len(self.values) < lookback or len(prices) < lookback:
            return False

        recent_rsi = self.values[-lookback:]
        recent_prices = prices[-lookback:]

        # Find highs
        rsi_high_idx = recent_rsi.index(max(recent_rsi))
        price_high_idx = recent_prices.index(max(recent_prices))

        # Check if we have two distinct highs
        if rsi_high_idx == len(recent_rsi) - 1 or price_high_idx == len(recent_prices) - 1:
            return False

        # Price makes higher high
        price_higher_high = recent_prices[-1] > recent_prices[price_high_idx]

        # RSI makes lower high
        rsi_lower_high = recent_rsi[-1] < recent_rsi[rsi_high_idx]

        return price_higher_high and rsi_lower_high

    def get_swing_lows(self, lookback: int = 5) -> List[float]:
        """
        Get swing lows from RSI values.

        Args:
            lookback: Number of periods to look back

        Returns:
            List of RSI swing low values
        """
        if len(self.values) < lookback:
            return []

        swing_lows = []
        recent_values = self.values[-lookback:]

        for i in range(1, len(recent_values) - 1):
            if recent_values[i] < recent_values[i - 1] and recent_values[i] < recent_values[i + 1]:
                swing_lows.append(recent_values[i])

        return swing_lows

    def get_swing_highs(self, lookback: int = 5) -> List[float]:
        """
        Get swing highs from RSI values.

        Args:
            lookback: Number of periods to look back

        Returns:
            List of RSI swing high values
        """
        if len(self.values) < lookback:
            return []

        swing_highs = []
        recent_values = self.values[-lookback:]

        for i in range(1, len(recent_values) - 1):
            if recent_values[i] > recent_values[i - 1] and recent_values[i] > recent_values[i + 1]:
                swing_highs.append(recent_values[i])

        return swing_highs

    def reset(self):
        """Reset RSI to initial state."""
        super().reset()
        self.gains = []
        self.losses = []
        self.avg_gain = None
        self.avg_loss = None
