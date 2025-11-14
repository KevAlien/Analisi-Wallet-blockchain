"""
Open Interest Strategy (for leveraged trading).

Interpretation based on Open Interest + Price Movement:

1. Price UP + OI UP = LONG BUILDUP (strong bullish sentiment) → LONG ENTRY
2. Price DOWN + OI DOWN = LONG UNWINDING (closing longs) → POTENTIAL BOTTOM
3. Price DOWN + OI UP = SHORT BUILDUP (strong bearish sentiment) → SHORT ENTRY
4. Price UP + OI DOWN = SHORT COVERING (closing shorts) → RELIEF BOUNCE

Entry Conditions LONG with OI:
- Long buildup identified (price up + OI up)
- Resistance breakout
- Volume expansion
- OI confirmation

Position Addition:
- On subsequent swings with OI confirmation

Exit:
- Supply absorption candle
- Significant OI reduction after target reached

NOTE: This strategy requires Open Interest data from exchanges.
For full implementation, integrate with exchange APIs (Binance Futures, etc.)
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from .base_strategy import BaseStrategy, TradingSignal, SignalType, SignalStrength
from ..indicators import Candle


class OpenInterestData:
    """
    Container for Open Interest data.

    In production, this would be fetched from exchange APIs like:
    - Binance Futures API
    - Bybit API
    - Deribit API
    """

    def __init__(self, timestamp: datetime, open_interest: float, price: float):
        """
        Initialize OI data point.

        Args:
            timestamp: Data timestamp
            open_interest: Open interest value (contracts or USD)
            price: Asset price at timestamp
        """
        self.timestamp = timestamp
        self.open_interest = open_interest
        self.price = price


class OpenInterestStrategy(BaseStrategy):
    """Trading strategy based on Open Interest analysis."""

    def __init__(self, oi_change_threshold: float = 5.0, price_change_threshold: float = 2.0,
                 timeframe: str = "1h"):
        """
        Initialize Open Interest strategy.

        Args:
            oi_change_threshold: Minimum OI change percentage to consider significant (default: 5%)
            price_change_threshold: Minimum price change percentage to consider significant (default: 2%)
            timeframe: Trading timeframe (default: "1h")
        """
        super().__init__(name="Open Interest", timeframe=timeframe)

        self.oi_change_threshold = oi_change_threshold
        self.price_change_threshold = price_change_threshold

        # OI data storage
        self.oi_data: List[OpenInterestData] = []

        # Track state
        self.in_position = False
        self.position_type: Optional[SignalType] = None
        self.entry_oi: Optional[float] = None

    def add_oi_data(self, timestamp: datetime, open_interest: float, price: float):
        """
        Add Open Interest data point.

        Args:
            timestamp: Data timestamp
            open_interest: Open interest value
            price: Asset price
        """
        self.oi_data.append(OpenInterestData(timestamp, open_interest, price))

        # Keep only recent data (e.g., last 100 points)
        if len(self.oi_data) > 100:
            self.oi_data.pop(0)

    def analyze(self, candles: List[Candle], current_oi: Optional[float] = None) -> Optional[TradingSignal]:
        """
        Analyze candles with Open Interest data.

        Args:
            candles: List of Candle objects
            current_oi: Current open interest value (optional, for real-time updates)

        Returns:
            TradingSignal if conditions are met, None otherwise
        """
        if not self.is_ready() or len(candles) < 2:
            return None

        # Add current OI data if provided
        if current_oi is not None:
            self.add_oi_data(candles[-1].timestamp, current_oi, candles[-1].close)

        if len(self.oi_data) < 2:
            return None

        current_candle = candles[-1]
        current_price = current_candle.close

        # Check for entry signals
        if not self.in_position:
            # Check for LONG entry
            long_signal = self._check_long_entry(candles, current_price)
            if long_signal:
                self.in_position = True
                self.position_type = SignalType.LONG
                self.entry_oi = self.oi_data[-1].open_interest
                self.add_signal(long_signal)
                return long_signal

            # Check for SHORT entry
            short_signal = self._check_short_entry(candles, current_price)
            if short_signal:
                self.in_position = True
                self.position_type = SignalType.SHORT
                self.entry_oi = self.oi_data[-1].open_interest
                self.add_signal(short_signal)
                return short_signal

        # Check for exit
        else:
            exit_signal = self._check_exit(candles, current_price)
            if exit_signal:
                self.in_position = False
                self.position_type = None
                self.entry_oi = None
                self.add_signal(exit_signal)
                return exit_signal

        return None

    def _check_long_entry(self, candles: List[Candle], current_price: float) -> Optional[TradingSignal]:
        """
        Check for LONG entry based on OI analysis.

        Condition: Price UP + OI UP = LONG BUILDUP (strong bullish)
        """
        # Calculate price change
        previous_price = self.oi_data[-2].price
        price_change_pct = ((current_price - previous_price) / previous_price) * 100

        # Calculate OI change
        current_oi = self.oi_data[-1].open_interest
        previous_oi = self.oi_data[-2].open_interest
        oi_change_pct = ((current_oi - previous_oi) / previous_oi) * 100

        reasons = []
        strength_score = 0

        # LONG BUILDUP: Price UP + OI UP
        if price_change_pct > self.price_change_threshold and oi_change_pct > self.oi_change_threshold:
            reasons.append(f"LONG BUILDUP detected (Price +{price_change_pct:.2f}%, OI +{oi_change_pct:.2f}%)")
            strength_score += 3
        else:
            return None  # No bullish OI pattern

        # Additional confirmations

        # 1. Resistance breakout
        resistance = self._find_resistance(candles)
        if resistance and current_price > resistance:
            reasons.append(f"Resistance broken at {resistance:.2f}")
            strength_score += 2

        # 2. Volume expansion
        if len(candles) >= 2 and candles[-1].volume > candles[-2].volume * 1.2:
            reasons.append("Volume expansion (+20%)")
            strength_score += 1

        # 3. Strong OI increase (>10%)
        if oi_change_pct > 10:
            reasons.append(f"Strong OI increase (+{oi_change_pct:.1f}%)")
            strength_score += 2

        # Calculate stop loss and take profit
        stop_loss = self.calculate_stop_loss(current_price, SignalType.LONG, candles, atr_multiplier=2.0)
        risk_reward = 3.0 if strength_score >= 6 else 2.0  # Higher R:R for strong signals
        take_profit = self.calculate_take_profit(current_price, stop_loss, risk_reward)

        # Determine signal strength
        if strength_score >= 7:
            strength = SignalStrength.VERY_STRONG
        elif strength_score >= 5:
            strength = SignalStrength.STRONG
        elif strength_score >= 3:
            strength = SignalStrength.MEDIUM
        else:
            strength = SignalStrength.WEAK

        return TradingSignal(
            signal_type=SignalType.LONG,
            strength=strength,
            price=current_price,
            timestamp=candles[-1].timestamp,
            strategy_name=self.name,
            reasons=reasons,
            indicators={
                'OI': current_oi,
                'OI_change_pct': oi_change_pct,
                'price_change_pct': price_change_pct,
                'pattern': 'LONG_BUILDUP',
            },
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=risk_reward
        )

    def _check_short_entry(self, candles: List[Candle], current_price: float) -> Optional[TradingSignal]:
        """
        Check for SHORT entry based on OI analysis.

        Condition: Price DOWN + OI UP = SHORT BUILDUP (strong bearish)
        """
        # Calculate price change
        previous_price = self.oi_data[-2].price
        price_change_pct = ((current_price - previous_price) / previous_price) * 100

        # Calculate OI change
        current_oi = self.oi_data[-1].open_interest
        previous_oi = self.oi_data[-2].open_interest
        oi_change_pct = ((current_oi - previous_oi) / previous_oi) * 100

        reasons = []
        strength_score = 0

        # SHORT BUILDUP: Price DOWN + OI UP
        if price_change_pct < -self.price_change_threshold and oi_change_pct > self.oi_change_threshold:
            reasons.append(f"SHORT BUILDUP detected (Price {price_change_pct:.2f}%, OI +{oi_change_pct:.2f}%)")
            strength_score += 3
        else:
            return None  # No bearish OI pattern

        # Additional confirmations

        # 1. Support breakdown
        support = self._find_support(candles)
        if support and current_price < support:
            reasons.append(f"Support broken at {support:.2f}")
            strength_score += 2

        # 2. Volume expansion
        if len(candles) >= 2 and candles[-1].volume > candles[-2].volume * 1.2:
            reasons.append("Volume expansion (+20%)")
            strength_score += 1

        # 3. Strong OI increase (>10%)
        if oi_change_pct > 10:
            reasons.append(f"Strong OI increase (+{oi_change_pct:.1f}%)")
            strength_score += 2

        # Calculate stop loss and take profit
        stop_loss = self.calculate_stop_loss(current_price, SignalType.SHORT, candles, atr_multiplier=2.0)
        risk_reward = 3.0 if strength_score >= 6 else 2.0
        take_profit = self.calculate_take_profit(current_price, stop_loss, risk_reward)

        # Determine signal strength
        if strength_score >= 7:
            strength = SignalStrength.VERY_STRONG
        elif strength_score >= 5:
            strength = SignalStrength.STRONG
        elif strength_score >= 3:
            strength = SignalStrength.MEDIUM
        else:
            strength = SignalStrength.WEAK

        return TradingSignal(
            signal_type=SignalType.SHORT,
            strength=strength,
            price=current_price,
            timestamp=candles[-1].timestamp,
            strategy_name=self.name,
            reasons=reasons,
            indicators={
                'OI': current_oi,
                'OI_change_pct': oi_change_pct,
                'price_change_pct': price_change_pct,
                'pattern': 'SHORT_BUILDUP',
            },
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=risk_reward
        )

    def _check_exit(self, candles: List[Candle], current_price: float) -> Optional[TradingSignal]:
        """Check for exit based on OI reduction or reversal patterns."""
        if not self.position_type or self.entry_oi is None:
            return None

        current_oi = self.oi_data[-1].open_interest
        oi_change_pct = ((current_oi - self.entry_oi) / self.entry_oi) * 100

        reasons = []

        # Significant OI reduction (position unwinding)
        if oi_change_pct < -5:
            reasons.append(f"Significant OI reduction ({oi_change_pct:.1f}%) - exit {self.position_type.value}")

        # Supply absorption (large candle with low volume)
        if len(candles) >= 2:
            current_candle = candles[-1]
            avg_volume = sum(c.volume for c in candles[-10:]) / 10
            if current_candle.body_size > avg_volume * 0.5 and current_candle.volume < avg_volume * 0.7:
                reasons.append("Supply absorption detected - exit position")

        if reasons:
            exit_type = SignalType.EXIT_LONG if self.position_type == SignalType.LONG else SignalType.EXIT_SHORT

            return TradingSignal(
                signal_type=exit_type,
                strength=SignalStrength.STRONG,
                price=current_price,
                timestamp=candles[-1].timestamp,
                strategy_name=self.name,
                reasons=reasons,
                indicators={
                    'OI': current_oi,
                    'OI_change_from_entry': oi_change_pct,
                }
            )

        return None

    def _find_resistance(self, candles: List[Candle], lookback: int = 20) -> Optional[float]:
        """Find recent resistance level."""
        if len(candles) < lookback:
            return None
        recent = candles[-lookback:]
        return max(c.high for c in recent[:-1])  # Exclude current candle

    def _find_support(self, candles: List[Candle], lookback: int = 20) -> Optional[float]:
        """Find recent support level."""
        if len(candles) < lookback:
            return None
        recent = candles[-lookback:]
        return min(c.low for c in recent[:-1])  # Exclude current candle

    def is_ready(self) -> bool:
        """Check if strategy has enough OI data."""
        return len(self.oi_data) >= 2

    def reset(self):
        """Reset strategy state."""
        super().reset()
        self.oi_data = []
        self.in_position = False
        self.position_type = None
        self.entry_oi = None
