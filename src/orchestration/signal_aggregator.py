"""
Signal Aggregator - Combines on-chain whale tracking signals with technical analysis signals.

This module integrates:
1. On-chain signals from whale tracking (existing system)
2. Technical analysis signals from trading strategies
3. AI reasoning for final decision making
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import logging

from ..signals.signal_generator import TradingSignal as OnChainSignal, SignalType as OnChainSignalType
from ..trading.strategies import TradingSignal as TASignal, SignalType, SignalStrength
from ..reasoning.agent_orchestrator import ReasoningAgentOrchestrator

logger = logging.getLogger(__name__)


class AggregatedSignalType(Enum):
    """Type of aggregated signal."""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    WEAK_BUY = "WEAK_BUY"
    NEUTRAL = "NEUTRAL"
    WEAK_SELL = "WEAK_SELL"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


@dataclass
class AggregatedSignal:
    """Combined signal from multiple sources."""
    signal_type: AggregatedSignalType
    confidence: float  # 0-100
    timestamp: datetime
    symbol: str
    price: float

    # Component signals
    on_chain_signals: List[OnChainSignal]
    ta_signals: List[TASignal]

    # AI analysis
    ai_reasoning: Optional[str] = None
    ai_recommendation: Optional[str] = None

    # Trade parameters
    recommended_entry: Optional[float] = None
    recommended_stop_loss: Optional[float] = None
    recommended_take_profit: Optional[float] = None
    recommended_position_size_pct: Optional[float] = None

    # Metadata
    contributing_factors: List[str] = None
    risk_level: str = "MEDIUM"

    def __post_init__(self):
        if self.contributing_factors is None:
            self.contributing_factors = []

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'signal_type': self.signal_type.value,
            'confidence': self.confidence,
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'price': self.price,
            'on_chain_signals_count': len(self.on_chain_signals),
            'ta_signals_count': len(self.ta_signals),
            'ai_reasoning': self.ai_reasoning,
            'ai_recommendation': self.ai_recommendation,
            'recommended_entry': self.recommended_entry,
            'recommended_stop_loss': self.recommended_stop_loss,
            'recommended_take_profit': self.recommended_take_profit,
            'recommended_position_size_pct': self.recommended_position_size_pct,
            'contributing_factors': self.contributing_factors,
            'risk_level': self.risk_level
        }


class SignalAggregator:
    """Aggregates signals from multiple sources."""

    def __init__(self, use_ai_reasoning: bool = True,
                 reasoning_agent: Optional[ReasoningAgentOrchestrator] = None):
        """
        Initialize Signal Aggregator.

        Args:
            use_ai_reasoning: Whether to use AI for final analysis (default: True)
            reasoning_agent: Optional existing ReasoningAgentOrchestrator instance
        """
        self.use_ai_reasoning = use_ai_reasoning
        self.reasoning_agent = reasoning_agent

        # Weighting factors for different signal sources
        self.weights = {
            'on_chain': 0.4,  # 40% weight for on-chain signals
            'ta': 0.6,  # 60% weight for technical analysis
        }

    def aggregate_signals(self, symbol: str, current_price: float,
                         on_chain_signals: List[OnChainSignal],
                         ta_signals: List[TASignal]) -> Optional[AggregatedSignal]:
        """
        Aggregate signals from multiple sources.

        Args:
            symbol: Trading symbol
            current_price: Current asset price
            on_chain_signals: On-chain whale tracking signals
            ta_signals: Technical analysis signals

        Returns:
            AggregatedSignal if actionable, None otherwise
        """
        if not on_chain_signals and not ta_signals:
            return None

        # Calculate scores for each source
        on_chain_score = self._score_on_chain_signals(on_chain_signals)
        ta_score = self._score_ta_signals(ta_signals)

        # Calculate weighted aggregate score
        aggregate_score = (
            on_chain_score * self.weights['on_chain'] +
            ta_score * self.weights['ta']
        )

        # Determine signal type based on aggregate score
        signal_type = self._determine_signal_type(aggregate_score)

        # Calculate confidence (0-100)
        confidence = self._calculate_confidence(on_chain_signals, ta_signals, aggregate_score)

        # Extract contributing factors
        contributing_factors = self._extract_contributing_factors(on_chain_signals, ta_signals)

        # Calculate trade parameters (use TA signals for these)
        entry, stop_loss, take_profit = self._calculate_trade_parameters(ta_signals, current_price)

        # Create aggregated signal
        aggregated = AggregatedSignal(
            signal_type=signal_type,
            confidence=confidence,
            timestamp=datetime.now(),
            symbol=symbol,
            price=current_price,
            on_chain_signals=on_chain_signals,
            ta_signals=ta_signals,
            recommended_entry=entry,
            recommended_stop_loss=stop_loss,
            recommended_take_profit=take_profit,
            contributing_factors=contributing_factors,
            risk_level=self._assess_risk_level(on_chain_signals, ta_signals)
        )

        # Apply AI reasoning if enabled
        if self.use_ai_reasoning and self.reasoning_agent:
            aggregated = self._apply_ai_reasoning(aggregated)

        return aggregated

    def _score_on_chain_signals(self, signals: List[OnChainSignal]) -> float:
        """
        Score on-chain signals.

        Returns score from -1 (bearish) to +1 (bullish)
        """
        if not signals:
            return 0.0

        score = 0.0
        for signal in signals:
            # Map signal types to scores
            if signal.signal_type == OnChainSignalType.ACCUMULATION:
                score += 1.0
            elif signal.signal_type == OnChainSignalType.EXCHANGE_WITHDRAWAL:
                score += 0.7
            elif signal.signal_type == OnChainSignalType.DISTRIBUTION:
                score -= 1.0
            elif signal.signal_type == OnChainSignalType.EXCHANGE_DEPOSIT:
                score -= 0.7
            elif signal.signal_type == OnChainSignalType.UNUSUAL_ACTIVITY:
                # Neutral, depends on context
                score += 0.0

            # Weight by signal strength
            strength_multiplier = {
                'LOW': 0.5,
                'MEDIUM': 0.75,
                'HIGH': 1.0,
                'VERY_HIGH': 1.25
            }.get(signal.strength.value, 1.0)

            score *= strength_multiplier

        # Normalize to -1 to +1
        return max(-1, min(1, score / max(len(signals), 1)))

    def _score_ta_signals(self, signals: List[TASignal]) -> float:
        """
        Score technical analysis signals.

        Returns score from -1 (bearish) to +1 (bullish)
        """
        if not signals:
            return 0.0

        score = 0.0
        for signal in signals:
            # Map signal types to scores
            if signal.signal_type == SignalType.LONG:
                score += 1.0
            elif signal.signal_type == SignalType.SHORT:
                score -= 1.0
            elif signal.signal_type in [SignalType.EXIT_LONG, SignalType.EXIT_SHORT]:
                score -= 0.5  # Exits are mild bearish/bullish signals

            # Weight by signal strength
            strength_multiplier = {
                SignalStrength.WEAK: 0.5,
                SignalStrength.MEDIUM: 0.75,
                SignalStrength.STRONG: 1.0,
                SignalStrength.VERY_STRONG: 1.25
            }.get(signal.strength, 1.0)

            score *= strength_multiplier

        # Normalize to -1 to +1
        return max(-1, min(1, score / max(len(signals), 1)))

    def _determine_signal_type(self, aggregate_score: float) -> AggregatedSignalType:
        """Determine signal type from aggregate score."""
        if aggregate_score >= 0.7:
            return AggregatedSignalType.STRONG_BUY
        elif aggregate_score >= 0.4:
            return AggregatedSignalType.BUY
        elif aggregate_score >= 0.1:
            return AggregatedSignalType.WEAK_BUY
        elif aggregate_score <= -0.7:
            return AggregatedSignalType.STRONG_SELL
        elif aggregate_score <= -0.4:
            return AggregatedSignalType.SELL
        elif aggregate_score <= -0.1:
            return AggregatedSignalType.WEAK_SELL
        else:
            return AggregatedSignalType.NEUTRAL

    def _calculate_confidence(self, on_chain_signals: List, ta_signals: List,
                             aggregate_score: float) -> float:
        """Calculate confidence level (0-100)."""
        # Base confidence on number of confirming signals
        total_signals = len(on_chain_signals) + len(ta_signals)
        signal_confidence = min(total_signals * 15, 60)  # Max 60 from signal count

        # Add confidence from aggregate score strength
        score_confidence = abs(aggregate_score) * 40  # Max 40 from score

        return min(signal_confidence + score_confidence, 100)

    def _extract_contributing_factors(self, on_chain_signals: List[OnChainSignal],
                                     ta_signals: List[TASignal]) -> List[str]:
        """Extract key contributing factors from signals."""
        factors = []

        # On-chain factors
        for signal in on_chain_signals[:3]:  # Top 3
            factors.append(f"On-chain: {signal.signal_type.value} ({signal.strength.value})")

        # TA factors
        for signal in ta_signals[:3]:  # Top 3
            factors.append(f"TA ({signal.strategy_name}): {signal.signal_type.value}")
            if signal.reasons:
                factors.extend(signal.reasons[:2])  # Top 2 reasons

        return factors[:10]  # Max 10 factors

    def _calculate_trade_parameters(self, ta_signals: List[TASignal],
                                   current_price: float) -> tuple:
        """Calculate recommended trade parameters from TA signals."""
        if not ta_signals:
            return current_price, None, None

        # Use the strongest signal for trade parameters
        strongest_signal = max(ta_signals, key=lambda s: s.strength.value if hasattr(s.strength, 'value') else 0)

        return (
            current_price,  # Entry at current price
            strongest_signal.stop_loss,
            strongest_signal.take_profit
        )

    def _assess_risk_level(self, on_chain_signals: List, ta_signals: List) -> str:
        """Assess overall risk level."""
        # High risk if signals disagree
        on_chain_score = self._score_on_chain_signals(on_chain_signals)
        ta_score = self._score_ta_signals(ta_signals)

        if (on_chain_score > 0 and ta_score < 0) or (on_chain_score < 0 and ta_score > 0):
            return "HIGH"  # Conflicting signals

        # Low risk if strong agreement
        if abs(on_chain_score - ta_score) < 0.2 and abs(on_chain_score) > 0.5:
            return "LOW"

        return "MEDIUM"

    def _apply_ai_reasoning(self, aggregated: AggregatedSignal) -> AggregatedSignal:
        """
        Apply AI reasoning to enhance the aggregated signal.

        Args:
            aggregated: Initial aggregated signal

        Returns:
            Enhanced aggregated signal with AI reasoning
        """
        if not self.reasoning_agent:
            return aggregated

        try:
            # TODO: Integrate with reasoning agent
            # For now, add placeholder AI reasoning
            aggregated.ai_reasoning = "AI analysis: Signal confluence detected across multiple timeframes"
            aggregated.ai_recommendation = f"Recommended action: {aggregated.signal_type.value}"

        except Exception as e:
            logger.warning(f"AI reasoning failed: {e}")

        return aggregated

    def is_actionable(self, signal: AggregatedSignal, min_confidence: float = 60.0) -> bool:
        """
        Check if signal is actionable (high enough confidence).

        Args:
            signal: Aggregated signal
            min_confidence: Minimum confidence required (default: 60%)

        Returns:
            True if signal is actionable
        """
        return (
            signal.confidence >= min_confidence and
            signal.signal_type != AggregatedSignalType.NEUTRAL
        )
