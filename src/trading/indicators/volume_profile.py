"""
Volume Profile Indicator.

Analyzes volume distribution across price levels to identify support/resistance zones.
"""
from typing import List, Optional, Dict, Tuple
from collections import defaultdict
from .base_indicator import BaseIndicator, Candle


class VolumeProfile(BaseIndicator):
    """
    Volume Profile analyzer.

    Identifies high volume nodes (HVN) and low volume nodes (LVN) which act as
    support/resistance levels.
    """

    def __init__(self, lookback: int = 100, num_bins: int = 50):
        """
        Initialize Volume Profile.

        Args:
            lookback: Number of candles to analyze
            num_bins: Number of price bins for volume distribution
        """
        super().__init__(period=lookback)
        self.lookback = lookback
        self.num_bins = num_bins
        self.volume_by_price: Dict[float, float] = {}
        self.hvn_levels: List[float] = []  # High Volume Nodes
        self.lvn_levels: List[float] = []  # Low Volume Nodes
        self.point_of_control: Optional[float] = None  # Price with highest volume

    def calculate(self, candles: List[Candle]) -> Optional[float]:
        """
        Calculate volume profile and identify key levels.

        Args:
            candles: List of Candle objects

        Returns:
            Point of Control (POC) - price level with highest volume
        """
        if len(candles) < self.lookback:
            return None

        recent_candles = candles[-self.lookback:]

        # Find price range
        price_min = min(c.low for c in recent_candles)
        price_max = max(c.high for c in recent_candles)
        price_range = price_max - price_min

        if price_range == 0:
            return None

        # Calculate bin size
        bin_size = price_range / self.num_bins

        # Initialize volume bins
        volume_bins: Dict[float, float] = defaultdict(float)

        # Distribute volume across price levels
        for candle in recent_candles:
            # Distribute candle volume across its range
            # Use typical price as the center
            typical_price = candle.typical_price

            # Find which bin this price falls into
            bin_index = int((typical_price - price_min) / bin_size)
            bin_index = min(bin_index, self.num_bins - 1)  # Ensure within bounds

            # Calculate bin price level
            bin_price = price_min + (bin_index * bin_size) + (bin_size / 2)

            # Add volume to this bin
            volume_bins[bin_price] += candle.volume

        self.volume_by_price = dict(volume_bins)

        # Find Point of Control (highest volume)
        if self.volume_by_price:
            self.point_of_control = max(
                self.volume_by_price.keys(),
                key=lambda p: self.volume_by_price[p]
            )

            # Identify High Volume Nodes (top 20% of volume)
            sorted_by_volume = sorted(
                self.volume_by_price.items(),
                key=lambda x: x[1],
                reverse=True
            )

            total_volume = sum(self.volume_by_price.values())
            cumulative_volume = 0
            self.hvn_levels = []

            for price, volume in sorted_by_volume:
                cumulative_volume += volume
                self.hvn_levels.append(price)

                # Take top 20% of volume
                if cumulative_volume >= total_volume * 0.2:
                    break

            # Identify Low Volume Nodes (bottom 20% of volume)
            self.lvn_levels = [
                price for price, volume in sorted_by_volume[-int(len(sorted_by_volume) * 0.2):]
            ]

        return self.point_of_control

    def is_high_volume_level(self, price: float, tolerance: float = 0.01) -> bool:
        """
        Check if a price level is a High Volume Node (potential support/resistance).

        Args:
            price: Price to check
            tolerance: Percentage tolerance

        Returns:
            True if price is near a high volume level
        """
        for hvn in self.hvn_levels:
            if abs(price - hvn) <= hvn * tolerance:
                return True
        return False

    def is_low_volume_level(self, price: float, tolerance: float = 0.01) -> bool:
        """
        Check if a price level is a Low Volume Node (breakout zone).

        Args:
            price: Price to check
            tolerance: Percentage tolerance

        Returns:
            True if price is near a low volume level
        """
        for lvn in self.lvn_levels:
            if abs(price - lvn) <= lvn * tolerance:
                return True
        return False

    def get_nearest_hvn(self, price: float) -> Optional[float]:
        """
        Get the nearest High Volume Node to a price.

        Args:
            price: Reference price

        Returns:
            Nearest HVN price level or None
        """
        if not self.hvn_levels:
            return None

        return min(self.hvn_levels, key=lambda hvn: abs(hvn - price))

    def get_support_levels(self, current_price: float, count: int = 3) -> List[float]:
        """
        Get HVN levels below current price (potential support).

        Args:
            current_price: Current price
            count: Number of support levels to return

        Returns:
            List of support levels
        """
        supports = [hvn for hvn in self.hvn_levels if hvn < current_price]
        supports.sort(reverse=True)  # Closest first
        return supports[:count]

    def get_resistance_levels(self, current_price: float, count: int = 3) -> List[float]:
        """
        Get HVN levels above current price (potential resistance).

        Args:
            current_price: Current price
            count: Number of resistance levels to return

        Returns:
            List of resistance levels
        """
        resistances = [hvn for hvn in self.hvn_levels if hvn > current_price]
        resistances.sort()  # Closest first
        return resistances[:count]

    def get_volume_at_price(self, price: float, tolerance: float = 0.005) -> float:
        """
        Get total volume traded at a specific price level.

        Args:
            price: Price level
            tolerance: Price tolerance

        Returns:
            Total volume at that price
        """
        total_volume = 0.0

        for level_price, volume in self.volume_by_price.items():
            if abs(level_price - price) <= price * tolerance:
                total_volume += volume

        return total_volume

    def get_value_area(self, percentage: float = 0.70) -> Optional[Tuple[float, float]]:
        """
        Calculate the Value Area (price range containing X% of volume).

        Args:
            percentage: Percentage of volume to include (default 70%)

        Returns:
            Tuple of (value_area_low, value_area_high) or None
        """
        if not self.volume_by_price or not self.point_of_control:
            return None

        total_volume = sum(self.volume_by_price.values())
        target_volume = total_volume * percentage

        # Sort prices by distance from POC
        sorted_prices = sorted(
            self.volume_by_price.keys(),
            key=lambda p: abs(p - self.point_of_control)
        )

        # Accumulate volume from POC outward
        cumulative_volume = 0.0
        value_area_prices = []

        for price in sorted_prices:
            cumulative_volume += self.volume_by_price[price]
            value_area_prices.append(price)

            if cumulative_volume >= target_volume:
                break

        if value_area_prices:
            return (min(value_area_prices), max(value_area_prices))

        return None

    def is_multi_touch_level(
        self,
        price: float,
        candles: List[Candle],
        min_touches: int = 2,
        tolerance: float = 0.01
    ) -> bool:
        """
        Check if a price level has been tested multiple times (support/resistance).

        Args:
            price: Price level to check
            candles: Recent candles
            min_touches: Minimum number of touches required
            tolerance: Price tolerance

        Returns:
            True if level has been tested >= min_touches times
        """
        touches = 0
        threshold = price * tolerance

        for candle in candles:
            # Check if candle touched this level
            if abs(candle.low - price) <= threshold or abs(candle.high - price) <= threshold:
                touches += 1

            if touches >= min_touches:
                return True

        return False
