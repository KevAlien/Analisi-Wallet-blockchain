"""
Base class for trading strategies.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from ..indicators import Candle


class SignalType(Enum):
    """Trading signal types."""
    LONG = "LONG"
    SHORT = "SHORT"
    EXIT_LONG = "EXIT_LONG"
    EXIT_SHORT = "EXIT_SHORT"
    NEUTRAL = "NEUTRAL"


class SignalStrength(Enum):
    """Signal strength levels."""
    WEAK = "WEAK"
    MEDIUM = "MEDIUM"
    STRONG = "STRONG"
    VERY_STRONG = "VERY_STRONG"


@dataclass
class TradingSignal:
    """Trading signal with metadata."""
    signal_type: SignalType
    strength: SignalStrength
    price: float
    timestamp: datetime
    strategy_name: str
    reasons: List[str]
    indicators: Dict[str, Any]
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_reward_ratio: Optional[float] = None

    def to_dict(self) -> dict:
        """Convert signal to dictionary."""
        return {
            'signal_type': self.signal_type.value,
            'strength': self.strength.value,
            'price': self.price,
            'timestamp': self.timestamp.isoformat(),
            'strategy_name': self.strategy_name,
            'reasons': self.reasons,
            'indicators': self.indicators,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'risk_reward_ratio': self.risk_reward_ratio,
        }


class BaseStrategy(ABC):
    """Base class for all trading strategies."""

    def __init__(self, name: str, timeframe: str = "5m"):
        """
        Initialize strategy.

        Args:
            name: Strategy name
            timeframe: Trading timeframe (e.g., "5m", "15m", "1h", "4h")
        """
        self.name = name
        self.timeframe = timeframe
        self.enabled = True
        self.signals: List[TradingSignal] = []

    @abstractmethod
    def analyze(self, candles: List[Candle]) -> Optional[TradingSignal]:
        """
        Analyze candles and generate trading signal.

        Args:
            candles: List of Candle objects

        Returns:
            TradingSignal if conditions are met, None otherwise
        """
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        """
        Check if strategy has enough data to generate signals.

        Returns:
            True if strategy is ready
        """
        pass

    def calculate_stop_loss(self, entry_price: float, signal_type: SignalType,
                          candles: List[Candle], atr_multiplier: float = 2.0) -> float:
        """
        Calculate stop loss level.

        Args:
            entry_price: Entry price for the trade
            signal_type: Type of signal (LONG/SHORT)
            candles: Recent candles for volatility calculation
            atr_multiplier: Multiplier for ATR-based stop loss

        Returns:
            Stop loss price level
        """
        if not candles:
            # Default: 2% stop loss
            multiplier = 0.98 if signal_type == SignalType.LONG else 1.02
            return entry_price * multiplier

        # Use recent swing high/low
        recent_candles = candles[-10:] if len(candles) >= 10 else candles

        if signal_type == SignalType.LONG:
            # For LONG: stop below recent swing low
            swing_low = min(c.low for c in recent_candles)
            # Add some buffer for volatility
            atr = self._calculate_atr(candles)
            return swing_low - (atr * atr_multiplier if atr else swing_low * 0.01)
        else:
            # For SHORT: stop above recent swing high
            swing_high = max(c.high for c in recent_candles)
            atr = self._calculate_atr(candles)
            return swing_high + (atr * atr_multiplier if atr else swing_high * 0.01)

    def calculate_take_profit(self, entry_price: float, stop_loss: float,
                            risk_reward_ratio: float = 2.0) -> float:
        """
        Calculate take profit level based on risk/reward ratio.

        Args:
            entry_price: Entry price for the trade
            stop_loss: Stop loss price level
            risk_reward_ratio: Desired risk/reward ratio

        Returns:
            Take profit price level
        """
        risk = abs(entry_price - stop_loss)
        reward = risk * risk_reward_ratio

        if entry_price > stop_loss:  # LONG position
            return entry_price + reward
        else:  # SHORT position
            return entry_price - reward

    def _calculate_atr(self, candles: List[Candle], period: int = 14) -> Optional[float]:
        """
        Calculate Average True Range for volatility.

        Args:
            candles: List of candles
            period: ATR period

        Returns:
            ATR value or None if insufficient data
        """
        if len(candles) < period + 1:
            return None

        true_ranges = []
        for i in range(1, len(candles)):
            high = candles[i].high
            low = candles[i].low
            prev_close = candles[i - 1].close

            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)

        recent_tr = true_ranges[-period:]
        return sum(recent_tr) / len(recent_tr)

    def add_signal(self, signal: TradingSignal):
        """
        Add signal to history.

        Args:
            signal: TradingSignal object
        """
        self.signals.append(signal)

    def get_latest_signal(self) -> Optional[TradingSignal]:
        """Get the most recent signal."""
        return self.signals[-1] if self.signals else None

    def get_signal_history(self, n: int = 10) -> List[TradingSignal]:
        """
        Get recent signal history.

        Args:
            n: Number of signals to retrieve

        Returns:
            List of recent signals
        """
        return self.signals[-n:] if len(self.signals) >= n else self.signals.copy()

    def enable(self):
        """Enable the strategy."""
        self.enabled = True

    def disable(self):
        """Disable the strategy."""
        self.enabled = False

    def reset(self):
        """Reset strategy to initial state."""
        self.signals = []

    def __str__(self) -> str:
        """String representation of strategy."""
        return f"{self.name} ({self.timeframe})"
