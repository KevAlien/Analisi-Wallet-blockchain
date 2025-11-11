"""
Enhanced signal with AI reasoning chains
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from .signal_generator import Signal, SignalType, SignalStrength

logger = logging.getLogger(__name__)


class EnhancedSignal(Signal):
    """
    Trading signal enhanced with AI reasoning

    Extends base Signal with:
    - Reasoning chain explaining the signal
    - Predicted market impact
    - Recommended actions
    - Correlation data
    - Market context
    """

    def __init__(
        self,
        signal_type: SignalType,
        strength: SignalStrength,
        transaction_hash: str,
        wallet_address: str,
        wallet_name: Optional[str],
        wallet_category: str,
        chain: str,
        value_eth: float,
        description: str,
        reasoning_chain: List[str],
        predicted_impact: str = "neutral",
        recommended_actions: Optional[List[str]] = None,
        correlations: Optional[List[str]] = None,
        market_context: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
        related_transactions: Optional[List[str]] = None,
        confidence: float = 0.0,
        tags: Optional[List[str]] = None,
    ):
        """
        Initialize enhanced signal

        Args:
            reasoning_chain: List of reasoning steps
            predicted_impact: bullish, bearish, or neutral
            recommended_actions: List of suggested actions
            correlations: Related correlation findings
            market_context: Current market conditions
            ... (other args from base Signal)
        """
        super().__init__(
            signal_type=signal_type,
            strength=strength,
            transaction_hash=transaction_hash,
            wallet_address=wallet_address,
            wallet_name=wallet_name,
            wallet_category=wallet_category,
            chain=chain,
            value_eth=value_eth,
            description=description,
            timestamp=timestamp,
            related_transactions=related_transactions,
            confidence=confidence,
            tags=tags
        )

        self.reasoning_chain = reasoning_chain or []
        self.predicted_impact = predicted_impact
        self.recommended_actions = recommended_actions or []
        self.correlations = correlations or []
        self.market_context = market_context or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert enhanced signal to dictionary"""
        base_dict = super().to_dict()

        base_dict.update({
            "reasoning_chain": self.reasoning_chain,
            "predicted_impact": self.predicted_impact,
            "recommended_actions": self.recommended_actions,
            "correlations": self.correlations,
            "market_context": self.market_context
        })

        return base_dict

    def get_message(self) -> str:
        """Get formatted message with reasoning for Telegram"""
        # Base message
        base_message = super().get_message()

        # Add reasoning section
        reasoning_section = "\n\n🧠 **AI REASONING:**\n"
        for i, step in enumerate(self.reasoning_chain, 1):
            reasoning_section += f"  {i}. {step}\n"

        # Add predicted impact
        impact_emoji = {
            "bullish": "📈",
            "bearish": "📉",
            "neutral": "➡️"
        }.get(self.predicted_impact, "➡️")

        impact_section = f"\n{impact_emoji} **Predicted Impact:** {self.predicted_impact.upper()}\n"

        # Add recommended actions
        actions_section = ""
        if self.recommended_actions:
            actions_section = "\n💡 **Recommended Actions:**\n"
            for action in self.recommended_actions:
                actions_section += f"  • {action}\n"

        # Add correlations if any
        correlations_section = ""
        if self.correlations:
            correlations_section = "\n🔗 **Correlations:**\n"
            for corr in self.correlations[:3]:  # Limit to 3
                correlations_section += f"  • {corr}\n"

        # Combine all sections
        full_message = (
            base_message +
            reasoning_section +
            impact_section +
            actions_section +
            correlations_section
        )

        return full_message

    @classmethod
    def from_reasoning_output(
        cls,
        reasoning_output: Dict[str, Any],
        wallet_info: Optional[Dict[str, Any]] = None
    ) -> 'EnhancedSignal':
        """
        Create EnhancedSignal from reasoning agent output

        Args:
            reasoning_output: Output from reasoning agent
            wallet_info: Optional wallet information

        Returns:
            EnhancedSignal instance
        """
        # Parse signal type
        signal_type_str = reasoning_output.get("signal_type", "unusual_activity")
        try:
            signal_type = SignalType[signal_type_str.upper()]
        except (KeyError, AttributeError):
            signal_type = SignalType.UNUSUAL_ACTIVITY

        # Parse strength
        strength_str = reasoning_output.get("strength", "medium")
        try:
            strength = SignalStrength[strength_str.upper()]
        except (KeyError, AttributeError):
            strength = SignalStrength.MEDIUM

        # Extract wallet info
        wallet_name = None
        wallet_category = "unknown"
        if wallet_info:
            wallet_name = wallet_info.get("name")
            wallet_category = wallet_info.get("category", "unknown")

        # Generate description from reasoning
        reasoning_chain = reasoning_output.get("reasoning_chain", [])
        description = reasoning_chain[0] if reasoning_chain else "AI-detected pattern"

        return cls(
            signal_type=signal_type,
            strength=strength,
            transaction_hash=reasoning_output.get("transaction_hash", "unknown"),
            wallet_address=reasoning_output.get("wallet_address", "unknown"),
            wallet_name=wallet_name,
            wallet_category=wallet_category,
            chain=reasoning_output.get("chain", "ethereum"),
            value_eth=reasoning_output.get("value_eth", 0),
            description=description,
            reasoning_chain=reasoning_chain,
            predicted_impact=reasoning_output.get("predicted_impact", "neutral"),
            recommended_actions=reasoning_output.get("recommended_actions", []),
            correlations=reasoning_output.get("correlations", []),
            market_context=reasoning_output.get("market_context", {}),
            confidence=reasoning_output.get("confidence", 0.5),
            tags=reasoning_output.get("tags", [])
        )


def create_signal_from_analysis(
    analysis: Dict[str, Any],
    enable_reasoning: bool = True
) -> Signal:
    """
    Factory function to create appropriate signal type

    Args:
        analysis: Analysis output (from reasoning agent or fallback)
        enable_reasoning: If True and reasoning available, create EnhancedSignal

    Returns:
        Signal or EnhancedSignal instance
    """
    source = analysis.get("source", "unknown")

    # If from reasoning agent and has reasoning chain, create EnhancedSignal
    if enable_reasoning and source == "reasoning_agent" and analysis.get("reasoning_chain"):
        return EnhancedSignal.from_reasoning_output(analysis)

    # Otherwise create basic Signal
    # Map signal_type string to SignalType enum
    signal_type_str = analysis.get("signal_type", "unusual_activity")
    try:
        signal_type = SignalType[signal_type_str.upper()]
    except (KeyError, AttributeError):
        signal_type = SignalType.UNUSUAL_ACTIVITY

    # Map strength string to SignalStrength enum
    strength_str = analysis.get("strength", "medium")
    try:
        strength = SignalStrength[strength_str.upper()]
    except (KeyError, AttributeError):
        strength = SignalStrength.MEDIUM

    return Signal(
        signal_type=signal_type,
        strength=strength,
        transaction_hash=analysis.get("transaction_hash", "unknown"),
        wallet_address=analysis.get("wallet_address", "unknown"),
        wallet_name=None,
        wallet_category="unknown",
        chain=analysis.get("chain", "ethereum"),
        value_eth=analysis.get("value_eth", 0),
        description=analysis.get("description", "Detected activity"),
        confidence=analysis.get("confidence", 0.5)
    )
