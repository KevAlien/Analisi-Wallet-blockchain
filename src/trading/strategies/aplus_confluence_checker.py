"""
A+ Setup Confluence Checker.

Validates that a trading setup has at least 4 out of 5 critical confluences:
1. Major structural level (weekly/daily S/R)
2. Confirmed RSI divergence
3. Specific candlestick pattern
4. Volume profile/OI alignment
5. EMA dynamical support/resistance

This increases win rate from 60-75% when all criteria are met.
"""
from typing import List, Optional, Dict
from dataclasses import dataclass
from .base_strategy import SignalType
from ..indicators import Candle
from ..indicators.rsi import RSI
from ..indicators.ema import EMA
from ..indicators.volume_profile import VolumeProfile
from ..indicators.candlestick_patterns import CandlestickPatterns


@dataclass
class ConfluenceResult:
    """Result of confluence check."""
    is_aplus: bool
    score: int  # Out of 5
    met_criteria: List[str]
    missing_criteria: List[str]
    details: Dict[str, any]


class APlusConfluenceChecker:
    """
    A+ Setup Confluence Checker.

    Validates trading setups against 5 critical criteria.
    Requires at least 4/5 for "A+" rating.
    """

    def __init__(
        self,
        rsi_period: int = 14,
        ema_periods: List[int] = [20, 50, 200],
        volume_profile_lookback: int = 100
    ):
        """
        Initialize A+ Confluence Checker.

        Args:
            rsi_period: RSI period for divergence detection
            ema_periods: EMA periods for support/resistance
            volume_profile_lookback: Volume profile lookback period
        """
        self.rsi = RSI(period=rsi_period)
        self.emas = {period: EMA(period=period) for period in ema_periods}
        self.volume_profile = VolumeProfile(lookback=volume_profile_lookback)
        self.candle_patterns = CandlestickPatterns()

    def check_confluence(
        self,
        candles: List[Candle],
        signal_type: SignalType,
        current_price: Optional[float] = None,
        open_interest: Optional[List[float]] = None
    ) -> ConfluenceResult:
        """
        Check if setup meets A+ confluence criteria.

        Args:
            candles: List of Candle objects
            signal_type: LONG or SHORT signal type
            current_price: Current price (uses last candle close if None)
            open_interest: Optional OI data

        Returns:
            ConfluenceResult with score and details
        """
        if not candles:
            return ConfluenceResult(
                is_aplus=False,
                score=0,
                met_criteria=[],
                missing_criteria=[],
                details={}
            )

        # Update indicators
        self.rsi.update(candles)
        for ema in self.emas.values():
            ema.update(candles)
        self.volume_profile.calculate(candles)
        self.candle_patterns.calculate(candles)

        if current_price is None:
            current_price = candles[-1].close

        score = 0
        met_criteria = []
        missing_criteria = []
        details = {}

        # 1. Check Major Structural Level (weekly/daily S/R)
        has_structural_level, struct_details = self._check_structural_level(
            candles, current_price, signal_type
        )
        if has_structural_level:
            score += 1
            met_criteria.append("Major structural level (S/R)")
        else:
            missing_criteria.append("Major structural level (S/R)")
        details['structural_level'] = struct_details

        # 2. Check RSI Divergence
        has_divergence, div_details = self._check_rsi_divergence(
            candles, signal_type
        )
        if has_divergence:
            score += 1
            met_criteria.append("Confirmed RSI divergence")
        else:
            missing_criteria.append("Confirmed RSI divergence")
        details['rsi_divergence'] = div_details

        # 3. Check Candlestick Pattern
        has_pattern, pattern_details = self._check_candlestick_pattern(
            signal_type
        )
        if has_pattern:
            score += 1
            met_criteria.append("Specific candlestick pattern")
        else:
            missing_criteria.append("Specific candlestick pattern")
        details['candlestick_pattern'] = pattern_details

        # 4. Check Volume Profile/OI Alignment
        has_volume_alignment, vol_details = self._check_volume_oi_alignment(
            candles, current_price, signal_type, open_interest
        )
        if has_volume_alignment:
            score += 1
            met_criteria.append("Volume profile/OI alignment")
        else:
            missing_criteria.append("Volume profile/OI alignment")
        details['volume_oi'] = vol_details

        # 5. Check EMA Dynamic Support/Resistance
        has_ema_support, ema_details = self._check_ema_support_resistance(
            current_price, signal_type
        )
        if has_ema_support:
            score += 1
            met_criteria.append("EMA dynamical support/resistance")
        else:
            missing_criteria.append("EMA dynamical support/resistance")
        details['ema_support'] = ema_details

        # A+ requires at least 4 out of 5
        is_aplus = score >= 4

        return ConfluenceResult(
            is_aplus=is_aplus,
            score=score,
            met_criteria=met_criteria,
            missing_criteria=missing_criteria,
            details=details
        )

    def _check_structural_level(
        self,
        candles: List[Candle],
        price: float,
        signal_type: SignalType
    ) -> tuple[bool, Dict]:
        """
        Check if price is at a major structural level.

        Uses volume profile high volume nodes as proxy for structural levels.
        """
        details = {}

        if signal_type == SignalType.LONG:
            # Check for support level
            support = self.volume_profile.get_nearest_hvn(price)
            if support and support < price:
                # Price near support
                distance = abs(price - support) / price
                if distance < 0.02:  # Within 2%
                    details['level'] = support
                    details['type'] = 'support'
                    details['distance'] = distance
                    return True, details

        elif signal_type == SignalType.SHORT:
            # Check for resistance level
            resistance = self.volume_profile.get_nearest_hvn(price)
            if resistance and resistance > price:
                # Price near resistance
                distance = abs(price - resistance) / price
                if distance < 0.02:  # Within 2%
                    details['level'] = resistance
                    details['type'] = 'resistance'
                    details['distance'] = distance
                    return True, details

        details['level'] = None
        return False, details

    def _check_rsi_divergence(
        self,
        candles: List[Candle],
        signal_type: SignalType
    ) -> tuple[bool, Dict]:
        """Check for RSI divergence."""
        details = {}

        if not self.rsi.is_ready() or len(candles) < 20:
            return False, details

        if signal_type == SignalType.LONG:
            # Check for bullish divergence
            has_div = self.rsi.detect_bullish_divergence(candles)
            details['type'] = 'bullish'
            details['detected'] = has_div
            return has_div, details

        elif signal_type == SignalType.SHORT:
            # Check for bearish divergence
            has_div = self.rsi.detect_bearish_divergence(candles)
            details['type'] = 'bearish'
            details['detected'] = has_div
            return has_div, details

        return False, details

    def _check_candlestick_pattern(
        self,
        signal_type: SignalType
    ) -> tuple[bool, Dict]:
        """Check for specific candlestick patterns."""
        details = {
            'patterns': self.candle_patterns.get_patterns()
        }

        if signal_type == SignalType.LONG:
            has_pattern = self.candle_patterns.has_bullish_pattern()
            details['required'] = 'bullish'
        elif signal_type == SignalType.SHORT:
            has_pattern = self.candle_patterns.has_bearish_pattern()
            details['required'] = 'bearish'
        else:
            has_pattern = False
            details['required'] = 'none'

        details['detected'] = has_pattern
        return has_pattern, details

    def _check_volume_oi_alignment(
        self,
        candles: List[Candle],
        price: float,
        signal_type: SignalType,
        open_interest: Optional[List[float]]
    ) -> tuple[bool, Dict]:
        """Check volume profile and OI alignment."""
        details = {}

        # Check volume profile
        if signal_type == SignalType.LONG:
            # Should be at high volume support
            at_hvn = self.volume_profile.is_high_volume_level(price)
            details['at_high_volume_node'] = at_hvn

            # OI increasing (if available)
            if open_interest and len(open_interest) >= 10:
                oi_increasing = sum(open_interest[-5:]) > sum(open_interest[-10:-5])
                details['oi_increasing'] = oi_increasing
                return at_hvn and oi_increasing, details
            else:
                details['oi_data'] = 'not available'
                return at_hvn, details

        elif signal_type == SignalType.SHORT:
            # Should be at high volume resistance
            at_hvn = self.volume_profile.is_high_volume_level(price)
            details['at_high_volume_node'] = at_hvn

            # OI increasing + price down (short buildup)
            if open_interest and len(open_interest) >= 10 and len(candles) >= 10:
                oi_increasing = sum(open_interest[-5:]) > sum(open_interest[-10:-5])
                price_down = sum(c.close for c in candles[-5:]) < sum(c.close for c in candles[-10:-5])
                details['oi_increasing'] = oi_increasing
                details['price_decreasing'] = price_down
                return at_hvn and oi_increasing and price_down, details
            else:
                details['oi_data'] = 'not available'
                return at_hvn, details

        return False, details

    def _check_ema_support_resistance(
        self,
        price: float,
        signal_type: SignalType
    ) -> tuple[bool, Dict]:
        """Check EMA dynamic support/resistance."""
        details = {}

        # Get EMA values
        ema_values = {period: ema.current_value for period, ema in self.emas.items()}
        details['ema_values'] = ema_values

        if not all(ema_values.values()):
            return False, details

        if signal_type == SignalType.LONG:
            # Price should be above EMAs (support)
            above_emas = all(price > val for val in ema_values.values() if val)

            # Bullish alignment (20 > 50 > 200)
            periods = sorted(ema_values.keys())
            if len(periods) >= 3:
                bullish_alignment = (
                    ema_values[periods[0]] > ema_values[periods[1]] > ema_values[periods[2]]
                )
            else:
                bullish_alignment = False

            details['above_emas'] = above_emas
            details['bullish_alignment'] = bullish_alignment

            return above_emas or bullish_alignment, details

        elif signal_type == SignalType.SHORT:
            # Price should be below EMAs (resistance)
            below_emas = all(price < val for val in ema_values.values() if val)

            # Bearish alignment (20 < 50 < 200)
            periods = sorted(ema_values.keys())
            if len(periods) >= 3:
                bearish_alignment = (
                    ema_values[periods[0]] < ema_values[periods[1]] < ema_values[periods[2]]
                )
            else:
                bearish_alignment = False

            details['below_emas'] = below_emas
            details['bearish_alignment'] = bearish_alignment

            return below_emas or bearish_alignment, details

        return False, details

    def is_ready(self) -> bool:
        """Check if all indicators are ready."""
        return (self.rsi.is_ready() and
                all(ema.is_ready() for ema in self.emas.values()))
