"""
Standard Deviation Indicator.

Calculates price standard deviation for detecting overextension and volatility.
"""
from typing import List, Optional
import statistics
from .base_indicator import BaseIndicator, Candle


class StandardDeviation(BaseIndicator):
    """
    Standard Deviation calculator.

    Measures price volatility and identifies when price is extended
    beyond normal ranges (Bollinger Band concept).
    """

    def __init__(self, period: int = 20, num_std: float = 2.0):
        """
        Initialize Standard Deviation.

        Args:
            period: Lookback period for calculation
            num_std: Number of standard deviations for bands
        """
        super().__init__(period=period)
        self.num_std = num_std
        self.mean: Optional[float] = None
        self.std_dev: Optional[float] = None
        self.upper_band: Optional[float] = None
        self.lower_band: Optional[float] = None

    def calculate(self, candles: List[Candle]) -> Optional[float]:
        """
        Calculate standard deviation of closing prices.

        Args:
            candles: List of Candle objects

        Returns:
            Current standard deviation value
        """
        if len(candles) < self.period:
            return None

        recent_closes = [c.close for c in candles[-self.period:]]

        # Calculate mean
        self.mean = statistics.mean(recent_closes)

        # Calculate standard deviation
        if len(recent_closes) > 1:
            self.std_dev = statistics.stdev(recent_closes)
        else:
            self.std_dev = 0.0

        # Calculate bands
        self.upper_band = self.mean + (self.num_std * self.std_dev)
        self.lower_band = self.mean - (self.num_std * self.std_dev)

        return self.std_dev

    def is_overextended_above(self, price: float, num_std: Optional[float] = None) -> bool:
        """
        Check if price is overextended above the mean.

        Args:
            price: Current price
            num_std: Number of standard deviations (uses default if None)

        Returns:
            True if price is above mean + (num_std * std_dev)
        """
        if self.mean is None or self.std_dev is None:
            return False

        std_threshold = num_std if num_std is not None else self.num_std
        threshold = self.mean + (std_threshold * self.std_dev)

        return price > threshold

    def is_overextended_below(self, price: float, num_std: Optional[float] = None) -> bool:
        """
        Check if price is overextended below the mean.

        Args:
            price: Current price
            num_std: Number of standard deviations (uses default if None)

        Returns:
            True if price is below mean - (num_std * std_dev)
        """
        if self.mean is None or self.std_dev is None:
            return False

        std_threshold = num_std if num_std is not None else self.num_std
        threshold = self.mean - (std_threshold * self.std_dev)

        return price < threshold

    def get_num_std_from_mean(self, price: float) -> Optional[float]:
        """
        Calculate how many standard deviations price is from mean.

        Args:
            price: Current price

        Returns:
            Number of standard deviations (positive = above, negative = below)
        """
        if self.mean is None or self.std_dev is None or self.std_dev == 0:
            return None

        return (price - self.mean) / self.std_dev

    def is_at_upper_band(self, price: float, tolerance: float = 0.01) -> bool:
        """
        Check if price is near the upper Bollinger Band.

        Args:
            price: Current price
            tolerance: Percentage tolerance

        Returns:
            True if price is near upper band
        """
        if self.upper_band is None:
            return False

        threshold = self.upper_band * tolerance
        return abs(price - self.upper_band) <= threshold

    def is_at_lower_band(self, price: float, tolerance: float = 0.01) -> bool:
        """
        Check if price is near the lower Bollinger Band.

        Args:
            price: Current price
            tolerance: Percentage tolerance

        Returns:
            True if price is near lower band
        """
        if self.lower_band is None:
            return False

        threshold = self.lower_band * tolerance
        return abs(price - self.lower_band) <= threshold

    def get_band_width(self) -> Optional[float]:
        """
        Calculate Bollinger Band width (volatility measure).

        Returns:
            Band width as percentage of mean
        """
        if self.upper_band is None or self.lower_band is None or self.mean is None:
            return None

        if self.mean == 0:
            return None

        band_width = (self.upper_band - self.lower_band) / self.mean
        return band_width

    def is_squeezing(self, threshold: float = 0.10) -> bool:
        """
        Check if bands are squeezing (low volatility).

        Args:
            threshold: Maximum band width ratio for squeeze

        Returns:
            True if bands are narrow (potential breakout setup)
        """
        band_width = self.get_band_width()
        if band_width is None:
            return False

        return band_width < threshold

    def is_expanding(self, candles: List[Candle], lookback: int = 5) -> bool:
        """
        Check if bands are expanding (increasing volatility).

        Args:
            candles: Recent candles
            lookback: Number of periods to compare

        Returns:
            True if band width is increasing
        """
        if len(candles) < lookback + self.period:
            return False

        # Calculate current band width
        current_width = self.get_band_width()
        if current_width is None:
            return False

        # Calculate previous band width
        prev_candles = candles[-(self.period + lookback):-lookback]
        prev_closes = [c.close for c in prev_candles]

        if len(prev_closes) < self.period:
            return False

        prev_mean = statistics.mean(prev_closes)
        prev_std = statistics.stdev(prev_closes) if len(prev_closes) > 1 else 0.0
        prev_upper = prev_mean + (self.num_std * prev_std)
        prev_lower = prev_mean - (self.num_std * prev_std)

        if prev_mean == 0:
            return False

        prev_width = (prev_upper - prev_lower) / prev_mean

        # Expanding if current width > previous width
        return current_width > prev_width * 1.1  # 10% increase

    def get_bands(self) -> tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Get current Bollinger Bands.

        Returns:
            Tuple of (lower_band, mean, upper_band)
        """
        return (self.lower_band, self.mean, self.upper_band)
