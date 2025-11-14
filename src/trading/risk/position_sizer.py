"""
Position Sizing Calculator.

Implements various position sizing methods:
- Fixed fractional (risk X% of capital per trade)
- Kelly Criterion (optimal position sizing based on win rate)
- Volatility-based (adjust size based on ATR/volatility)
"""
from typing import Optional
from enum import Enum


class PositionSizingMethod(Enum):
    """Position sizing methods."""
    FIXED_FRACTIONAL = "fixed_fractional"
    KELLY_CRITERION = "kelly_criterion"
    VOLATILITY_BASED = "volatility_based"
    FIXED_AMOUNT = "fixed_amount"


class PositionSizer:
    """Calculate position sizes based on risk management rules."""

    def __init__(self, method: PositionSizingMethod = PositionSizingMethod.FIXED_FRACTIONAL,
                 risk_per_trade_pct: float = 1.0, max_position_pct: float = 10.0):
        """
        Initialize Position Sizer.

        Args:
            method: Position sizing method (default: FIXED_FRACTIONAL)
            risk_per_trade_pct: Risk percentage per trade (default: 1.0%)
            max_position_pct: Maximum position size as % of capital (default: 10%)
        """
        self.method = method
        self.risk_per_trade_pct = risk_per_trade_pct
        self.max_position_pct = max_position_pct

    def calculate_position_size(self, capital: float, entry_price: float,
                               stop_loss_price: float, win_rate: Optional[float] = None,
                               avg_win: Optional[float] = None,
                               avg_loss: Optional[float] = None) -> float:
        """
        Calculate position size.

        Args:
            capital: Total available capital
            entry_price: Entry price for the trade
            stop_loss_price: Stop loss price level
            win_rate: Historical win rate (0-1), required for Kelly Criterion
            avg_win: Average win amount (%), required for Kelly Criterion
            avg_loss: Average loss amount (%), required for Kelly Criterion

        Returns:
            Position size in base currency units
        """
        if self.method == PositionSizingMethod.FIXED_FRACTIONAL:
            return self._fixed_fractional(capital, entry_price, stop_loss_price)

        elif self.method == PositionSizingMethod.KELLY_CRITERION:
            if win_rate is None or avg_win is None or avg_loss is None:
                # Fallback to fixed fractional if Kelly parameters missing
                return self._fixed_fractional(capital, entry_price, stop_loss_price)
            return self._kelly_criterion(capital, entry_price, stop_loss_price,
                                        win_rate, avg_win, avg_loss)

        elif self.method == PositionSizingMethod.VOLATILITY_BASED:
            return self._volatility_based(capital, entry_price, stop_loss_price)

        elif self.method == PositionSizingMethod.FIXED_AMOUNT:
            return self._fixed_amount(capital, entry_price)

        else:
            return self._fixed_fractional(capital, entry_price, stop_loss_price)

    def _fixed_fractional(self, capital: float, entry_price: float,
                         stop_loss_price: float) -> float:
        """
        Fixed fractional position sizing.

        Risk a fixed percentage of capital per trade.

        Formula:
        Position Size = (Capital × Risk%) / (Entry Price - Stop Loss)
        """
        risk_amount = capital * (self.risk_per_trade_pct / 100)
        stop_distance = abs(entry_price - stop_loss_price)

        if stop_distance == 0:
            return 0.0

        position_size = risk_amount / stop_distance

        # Apply maximum position size limit
        max_position = capital * (self.max_position_pct / 100) / entry_price
        return min(position_size, max_position)

    def _kelly_criterion(self, capital: float, entry_price: float,
                        stop_loss_price: float, win_rate: float,
                        avg_win_pct: float, avg_loss_pct: float) -> float:
        """
        Kelly Criterion position sizing.

        Formula:
        Kelly% = (Win Rate × Avg Win - (1 - Win Rate) × Avg Loss) / Avg Win

        We then use Kelly% to determine position size.
        """
        # Calculate Kelly percentage
        kelly_pct = (win_rate * avg_win_pct - (1 - win_rate) * avg_loss_pct) / avg_win_pct

        # Use half Kelly (more conservative)
        kelly_pct = kelly_pct * 0.5

        # Ensure Kelly is positive and within bounds
        kelly_pct = max(0, min(kelly_pct, self.max_position_pct / 100))

        # Calculate position size
        position_value = capital * kelly_pct
        position_size = position_value / entry_price

        return position_size

    def _volatility_based(self, capital: float, entry_price: float,
                         stop_loss_price: float) -> float:
        """
        Volatility-based position sizing.

        Adjust position size based on volatility (measured by stop distance).
        Higher volatility = smaller position.
        """
        # Calculate stop distance as percentage
        stop_distance_pct = abs(entry_price - stop_loss_price) / entry_price

        # Inverse relationship: higher volatility = smaller position
        # Target risk: risk_per_trade_pct
        position_pct = (self.risk_per_trade_pct / 100) / stop_distance_pct

        # Apply limits
        position_pct = min(position_pct, self.max_position_pct / 100)

        position_size = (capital * position_pct) / entry_price

        return position_size

    def _fixed_amount(self, capital: float, entry_price: float) -> float:
        """Fixed amount position sizing (e.g., always use 5% of capital)."""
        position_value = capital * (self.risk_per_trade_pct / 100)
        return position_value / entry_price

    def calculate_risk_reward_ratio(self, entry_price: float, stop_loss: float,
                                   take_profit: float) -> float:
        """
        Calculate risk/reward ratio for a trade.

        Formula:
        R:R = (Take Profit - Entry) / (Entry - Stop Loss)

        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price

        Returns:
            Risk/reward ratio
        """
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)

        if risk == 0:
            return 0.0

        return reward / risk

    def minimum_win_rate_required(self, risk_reward_ratio: float) -> float:
        """
        Calculate minimum win rate required for profitability.

        Formula:
        Min Win Rate = 1 / (1 + R:R)

        Args:
            risk_reward_ratio: Risk/reward ratio

        Returns:
            Minimum win rate (0-1) required for breakeven
        """
        return 1 / (1 + risk_reward_ratio)

    def expected_profitability(self, win_rate: float, avg_win_pct: float,
                              avg_loss_pct: float) -> float:
        """
        Calculate expected profitability per trade.

        Formula:
        Expected Profit = (Win Rate × Avg Win) - ((1 - Win Rate) × Avg Loss)

        Args:
            win_rate: Historical win rate (0-1)
            avg_win_pct: Average win percentage
            avg_loss_pct: Average loss percentage

        Returns:
            Expected profit percentage per trade
        """
        return (win_rate * avg_win_pct) - ((1 - win_rate) * avg_loss_pct)

    def validate_position(self, position_size: float, entry_price: float,
                         capital: float) -> tuple[bool, str]:
        """
        Validate if position size is acceptable.

        Args:
            position_size: Calculated position size
            entry_price: Entry price
            capital: Available capital

        Returns:
            Tuple of (is_valid, reason)
        """
        position_value = position_size * entry_price

        # Check if position exceeds available capital
        if position_value > capital:
            return False, "Position size exceeds available capital"

        # Check if position exceeds maximum position size
        max_position_value = capital * (self.max_position_pct / 100)
        if position_value > max_position_value:
            return False, f"Position exceeds maximum size ({self.max_position_pct}% of capital)"

        # Check if position is too small (e.g., less than 0.1% of capital)
        min_position_value = capital * 0.001
        if position_value < min_position_value:
            return False, "Position size too small (< 0.1% of capital)"

        return True, "Position valid"

    def adjust_for_leverage(self, position_size: float, leverage: float) -> float:
        """
        Adjust position size for leverage.

        Args:
            position_size: Base position size
            leverage: Leverage multiplier (e.g., 2 for 2x, 10 for 10x)

        Returns:
            Leveraged position size
        """
        return position_size * leverage

    def calculate_margin_required(self, position_size: float, entry_price: float,
                                  leverage: float = 1.0) -> float:
        """
        Calculate margin required for a position.

        Args:
            position_size: Position size in base currency
            entry_price: Entry price
            leverage: Leverage multiplier (default: 1.0 for no leverage)

        Returns:
            Margin required
        """
        position_value = position_size * entry_price
        return position_value / leverage
