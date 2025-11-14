"""
Portfolio Tracker for monitoring open positions, PnL, and performance metrics.
"""
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class PositionStatus(Enum):
    """Position status."""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PENDING = "PENDING"


@dataclass
class Position:
    """Represents a trading position."""
    symbol: str
    entry_price: float
    size: float
    side: str  # "LONG" or "SHORT"
    entry_time: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    status: PositionStatus = PositionStatus.OPEN
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    pnl: float = 0.0
    pnl_pct: float = 0.0
    fees: float = 0.0
    strategy_name: str = ""
    metadata: Dict = field(default_factory=dict)

    def update_pnl(self, current_price: float):
        """Update unrealized PnL."""
        if self.side == "LONG":
            self.pnl = (current_price - self.entry_price) * self.size
            self.pnl_pct = ((current_price - self.entry_price) / self.entry_price) * 100
        else:  # SHORT
            self.pnl = (self.entry_price - current_price) * self.size
            self.pnl_pct = ((self.entry_price - current_price) / self.entry_price) * 100

    def close_position(self, exit_price: float, exit_time: datetime):
        """Close the position."""
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.status = PositionStatus.CLOSED
        self.update_pnl(exit_price)


class PortfolioTracker:
    """Track portfolio positions and performance."""

    def __init__(self, initial_capital: float):
        """Initialize portfolio tracker."""
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions: List[Position] = []
        self.closed_positions: List[Position] = []

    def add_position(self, position: Position):
        """Add new position."""
        self.positions.append(position)

    def close_position(self, symbol: str, exit_price: float, exit_time: datetime):
        """Close a position."""
        for pos in self.positions:
            if pos.symbol == symbol and pos.status == PositionStatus.OPEN:
                pos.close_position(exit_price, exit_time)
                self.current_capital += pos.pnl - pos.fees
                self.closed_positions.append(pos)
                self.positions.remove(pos)
                break

    def get_open_positions(self) -> List[Position]:
        """Get all open positions."""
        return [p for p in self.positions if p.status == PositionStatus.OPEN]

    def get_total_pnl(self, current_prices: Dict[str, float]) -> float:
        """Calculate total PnL (realized + unrealized)."""
        unrealized = sum(
            self._calculate_position_pnl(p, current_prices.get(p.symbol, p.entry_price))
            for p in self.get_open_positions()
        )
        realized = sum(p.pnl for p in self.closed_positions)
        return realized + unrealized

    def _calculate_position_pnl(self, position: Position, current_price: float) -> float:
        """Calculate PnL for a position."""
        if position.side == "LONG":
            return (current_price - position.entry_price) * position.size
        else:
            return (position.entry_price - current_price) * position.size

    def get_performance_metrics(self) -> Dict:
        """Calculate performance metrics."""
        if not self.closed_positions:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
                'total_pnl': 0.0,
                'total_return_pct': 0.0
            }

        wins = [p for p in self.closed_positions if p.pnl > 0]
        losses = [p for p in self.closed_positions if p.pnl < 0]

        total_wins = sum(p.pnl for p in wins)
        total_losses = abs(sum(p.pnl for p in losses))

        return {
            'total_trades': len(self.closed_positions),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': len(wins) / len(self.closed_positions) if self.closed_positions else 0,
            'avg_win': total_wins / len(wins) if wins else 0,
            'avg_loss': total_losses / len(losses) if losses else 0,
            'profit_factor': total_wins / total_losses if total_losses > 0 else 0,
            'total_pnl': sum(p.pnl for p in self.closed_positions),
            'total_return_pct': ((self.current_capital - self.initial_capital) / self.initial_capital) * 100,
            'max_win': max((p.pnl for p in wins), default=0),
            'max_loss': min((p.pnl for p in losses), default=0),
        }

    def check_stop_loss(self, position: Position, current_price: float) -> bool:
        """Check if stop loss is hit."""
        if position.stop_loss is None:
            return False

        if position.side == "LONG":
            return current_price <= position.stop_loss
        else:  # SHORT
            return current_price >= position.stop_loss

    def check_take_profit(self, position: Position, current_price: float) -> bool:
        """Check if take profit is hit."""
        if position.take_profit is None:
            return False

        if position.side == "LONG":
            return current_price >= position.take_profit
        else:  # SHORT
            return current_price <= position.take_profit

    def get_max_drawdown(self) -> float:
        """Calculate maximum drawdown."""
        if not self.closed_positions:
            return 0.0

        peak = self.initial_capital
        max_dd = 0.0
        current = self.initial_capital

        for pos in self.closed_positions:
            current += pos.pnl
            if current > peak:
                peak = current
            dd = (peak - current) / peak
            max_dd = max(max_dd, dd)

        return max_dd * 100  # Return as percentage

    def risk_check(self, max_open_positions: int = 5, max_risk_pct: float = 20.0) -> tuple[bool, str]:
        """Check if new position can be opened based on risk limits."""
        if len(self.get_open_positions()) >= max_open_positions:
            return False, f"Maximum open positions reached ({max_open_positions})"

        total_risk = sum(
            abs(p.entry_price - p.stop_loss) * p.size
            for p in self.get_open_positions()
            if p.stop_loss
        )
        risk_pct = (total_risk / self.current_capital) * 100

        if risk_pct >= max_risk_pct:
            return False, f"Total portfolio risk too high ({risk_pct:.1f}%)"

        return True, "Risk check passed"
