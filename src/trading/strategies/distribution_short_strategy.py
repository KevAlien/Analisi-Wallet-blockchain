"""
Distribution-triggered Short Entry Strategy

This strategy opens SHORT positions when:
1. Whale DISTRIBUTION signals are detected (bearish on-chain activity)
2. Price is at a higher low level (potential trend reversal point)
3. Market shows signs of weakness despite uptrend structure

Key Features:
- Combines on-chain whale tracking with technical price structure
- Identifies optimal short entry at higher low levels
- Targets trend reversals after distribution activity
"""
from typing import List, Optional
import logging

from .base_strategy import BaseStrategy, TradingSignal, SignalType, SignalStrength
from ..indicators.base_indicator import Candle
from ..indicators.swing_points import SwingPointDetector
from ..indicators.pivot_points import PivotPoints
from ..indicators.rsi import RSI
from ...signals.signal_generator import Signal as OnChainSignal, SignalType as OnChainSignalType

logger = logging.getLogger(__name__)


class DistributionShortStrategy(BaseStrategy):
    """
    Strategy that opens SHORT positions when whale distribution
    coincides with price at higher low levels.

    This is the core implementation of the requested feature:
    "Add open short position at the higher low level when predicted impact is bearish"
    """

    def __init__(
        self,
        swing_lookback: int = 5,
        min_distribution_strength: str = "HIGH",
        price_tolerance: float = 0.005,
        require_rsi_confirmation: bool = True,
        rsi_period: int = 14,
        rsi_overbought: float = 70.0
    ):
        """
        Initialize Distribution Short Strategy.

        Args:
            swing_lookback: Number of candles for swing point detection
            min_distribution_strength: Minimum strength for distribution signals
            price_tolerance: Price tolerance for higher low level (0.5% default)
            require_rsi_confirmation: Require RSI overbought confirmation
            rsi_period: RSI period
            rsi_overbought: RSI overbought threshold
        """
        super().__init__(name="DistributionShort")

        self.swing_detector = SwingPointDetector(lookback=swing_lookback)
        self.pivot_points = PivotPoints()
        self.rsi = RSI(period=rsi_period)

        self.min_distribution_strength = min_distribution_strength
        self.price_tolerance = price_tolerance
        self.require_rsi_confirmation = require_rsi_confirmation
        self.rsi_overbought = rsi_overbought

        # Track distribution signals
        self.recent_distribution_signals: List[OnChainSignal] = []

    def analyze(
        self,
        candles: List[Candle],
        on_chain_signals: Optional[List[OnChainSignal]] = None
    ) -> Optional[TradingSignal]:
        """
        Analyze market and generate SHORT signals based on distribution + higher low.

        Args:
            candles: List of price candles
            on_chain_signals: Optional list of on-chain signals

        Returns:
            TradingSignal if conditions met, None otherwise
        """
        if len(candles) < 30:  # Need sufficient history
            return None

        current_candle = candles[-1]
        current_price = current_candle.close

        # Update indicators
        self.swing_detector.calculate(candles)
        self.pivot_points.calculate(candles)
        rsi_value = self.rsi.calculate(candles)

        # Step 1: Check for recent distribution signals
        distribution_detected = self._check_distribution_signals(on_chain_signals)
        if not distribution_detected:
            return None

        # Step 2: Check if we're at a higher low level
        at_higher_low, entry_conditions = self._check_higher_low_entry(current_price)
        if not at_higher_low:
            return None

        # Step 3: Optional RSI confirmation
        if self.require_rsi_confirmation:
            if rsi_value is None or rsi_value < self.rsi_overbought:
                logger.debug(
                    f"RSI confirmation failed: RSI={rsi_value}, "
                    f"required > {self.rsi_overbought}"
                )
                return None

        # Step 4: Check for additional bearish confirmations
        strength = self._calculate_signal_strength(
            entry_conditions,
            rsi_value,
            distribution_detected
        )

        # Step 5: Calculate stop loss and take profit
        stop_loss = self._calculate_stop_loss_for_short(candles, entry_conditions)
        take_profit = self._calculate_take_profit_for_short(
            current_price, stop_loss, entry_conditions
        )

        # Build reasons for the signal
        reasons = self._build_signal_reasons(
            entry_conditions,
            rsi_value,
            distribution_detected
        )

        logger.info(
            f"SHORT signal generated: Price={current_price:.2f}, "
            f"Entry={entry_conditions.get('entry_level')}, "
            f"SL={stop_loss}, TP={take_profit}, Strength={strength}"
        )

        return TradingSignal(
            signal_type=SignalType.SHORT,
            strength=strength,
            strategy_name=self.name,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reasons=reasons,
            metadata={
                "entry_conditions": entry_conditions,
                "distribution_count": len(self.recent_distribution_signals),
                "rsi": rsi_value,
                "trend": entry_conditions.get("trend")
            }
        )

    def _check_distribution_signals(
        self,
        on_chain_signals: Optional[List[OnChainSignal]]
    ) -> bool:
        """
        Check if there are recent significant distribution signals.

        Args:
            on_chain_signals: List of on-chain signals

        Returns:
            True if distribution signals detected
        """
        if not on_chain_signals:
            return False

        # Filter for distribution signals
        distribution_signals = [
            signal for signal in on_chain_signals
            if signal.signal_type == OnChainSignalType.DISTRIBUTION
        ]

        # Check for high-strength distribution signals
        strong_distributions = [
            signal for signal in distribution_signals
            if signal.strength.value in ["HIGH", "VERY_HIGH"]
        ]

        if strong_distributions:
            self.recent_distribution_signals = strong_distributions
            logger.info(
                f"Distribution detected: {len(strong_distributions)} strong signals"
            )
            return True

        return False

    def _check_higher_low_entry(
        self,
        current_price: float
    ) -> tuple[bool, dict]:
        """
        Check if current price is at a higher low level suitable for SHORT entry.

        Args:
            current_price: Current market price

        Returns:
            Tuple of (should_enter, entry_conditions)
        """
        # Get entry conditions from swing detector
        entry_conditions = self.swing_detector.get_short_entry_conditions(
            current_price,
            self.price_tolerance
        )

        # Check if we should enter short at higher low
        should_enter = entry_conditions.get("should_enter_short", False)

        if should_enter:
            logger.info(
                f"Higher low entry detected: "
                f"Entry={entry_conditions.get('entry_level')}, "
                f"Trend={entry_conditions.get('trend')}"
            )

        return should_enter, entry_conditions

    def _calculate_signal_strength(
        self,
        entry_conditions: dict,
        rsi_value: Optional[float],
        distribution_detected: bool
    ) -> SignalStrength:
        """
        Calculate the strength of the SHORT signal.

        Args:
            entry_conditions: Entry conditions from swing detector
            rsi_value: Current RSI value
            distribution_detected: Whether distribution was detected

        Returns:
            SignalStrength
        """
        strength_score = 0

        # Distribution signals add strength
        if distribution_detected:
            dist_count = len(self.recent_distribution_signals)
            if dist_count >= 3:
                strength_score += 2
            elif dist_count >= 2:
                strength_score += 1

        # Weakening uptrend is stronger signal
        if entry_conditions.get("uptrend_weakening", False):
            strength_score += 2

        # Lower high adds confirmation
        if entry_conditions.get("is_lower_high", False):
            strength_score += 1

        # RSI overbought adds strength
        if rsi_value and rsi_value >= self.rsi_overbought:
            if rsi_value >= 80:
                strength_score += 2
            else:
                strength_score += 1

        # Map score to strength
        if strength_score >= 5:
            return SignalStrength.VERY_STRONG
        elif strength_score >= 3:
            return SignalStrength.STRONG
        elif strength_score >= 1:
            return SignalStrength.MEDIUM
        else:
            return SignalStrength.WEAK

    def _calculate_stop_loss_for_short(
        self,
        candles: List[Candle],
        entry_conditions: dict
    ) -> float:
        """
        Calculate stop loss for SHORT position.

        For SHORT positions, stop loss is above entry (at recent swing high).

        Args:
            candles: Price candles
            entry_conditions: Entry conditions with swing levels

        Returns:
            Stop loss price
        """
        # Use the last swing high as stop loss
        last_swing_high = entry_conditions.get("last_swing_high")

        if last_swing_high:
            # Add small buffer above swing high
            stop_loss = last_swing_high * 1.005  # 0.5% buffer
            return stop_loss

        # Fallback: use recent high + ATR
        current_price = candles[-1].close
        atr = self._calculate_atr(candles)
        return current_price + (2 * atr)

    def _calculate_take_profit_for_short(
        self,
        entry_price: float,
        stop_loss: float,
        entry_conditions: dict
    ) -> float:
        """
        Calculate take profit for SHORT position.

        For SHORT positions, take profit is below entry.
        Use 2:1 reward-to-risk ratio.

        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            entry_conditions: Entry conditions

        Returns:
            Take profit price
        """
        # Calculate risk (distance from entry to stop loss)
        risk = stop_loss - entry_price

        # Target 2:1 reward-to-risk
        reward = risk * 2

        # Take profit is below entry for SHORT
        take_profit = entry_price - reward

        # Use last swing low as alternative target
        last_swing_low = entry_conditions.get("last_swing_low")
        if last_swing_low:
            # Use the closer of the two targets (more conservative)
            take_profit = max(take_profit, last_swing_low * 0.995)

        return take_profit

    def _build_signal_reasons(
        self,
        entry_conditions: dict,
        rsi_value: Optional[float],
        distribution_detected: bool
    ) -> List[str]:
        """
        Build list of reasons for the SHORT signal.

        Args:
            entry_conditions: Entry conditions
            rsi_value: RSI value
            distribution_detected: Distribution detection status

        Returns:
            List of reason strings
        """
        reasons = []

        if distribution_detected:
            count = len(self.recent_distribution_signals)
            reasons.append(
                f"Whale distribution detected ({count} strong signal(s))"
            )

        if entry_conditions.get("is_higher_low"):
            reasons.append(
                f"Price at higher low level: {entry_conditions.get('entry_level'):.2f}"
            )

        if entry_conditions.get("uptrend_weakening"):
            reasons.append("Uptrend showing signs of weakness")

        if entry_conditions.get("is_lower_high"):
            reasons.append("Lower high formed - potential reversal")

        if rsi_value and rsi_value >= self.rsi_overbought:
            reasons.append(f"RSI overbought: {rsi_value:.1f}")

        trend = entry_conditions.get("trend", "uncertain")
        reasons.append(f"Market trend: {trend}")

        return reasons

    def reset(self):
        """Reset strategy state."""
        super().reset()
        self.swing_detector.reset()
        self.pivot_points.reset()
        self.rsi.reset()
        self.recent_distribution_signals = []
