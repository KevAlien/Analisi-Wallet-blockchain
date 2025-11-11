"""
Wallet profiler
Creates behavioral profiles for wallets
"""
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class WalletProfiler:
    """
    Creates behavioral profiles for wallets

    Generates:
    - Trading style classification
    - Risk profile
    - Activity patterns
    - Success rate estimates
    """

    def __init__(self, context_memory):
        """
        Initialize profiler

        Args:
            context_memory: ContextMemory instance
        """
        self.memory = context_memory

    async def profile_wallet(self, wallet_address: str) -> Dict[str, Any]:
        """
        Create comprehensive profile for a wallet

        Args:
            wallet_address: Wallet address to profile

        Returns:
            Wallet profile dict
        """
        history = self.memory.get_wallet_history(wallet_address, hours=24 * 30)  # Last month

        if not history:
            return {
                "has_profile": False,
                "message": "Insufficient data for profiling"
            }

        stats = self.memory.get_wallet_statistics(wallet_address)

        # Classify trading style
        trading_style = self._classify_trading_style(history, stats)

        # Determine risk profile
        risk_profile = self._determine_risk_profile(history, stats)

        # Analyze success indicators
        success_indicators = self._analyze_success_indicators(history)

        # Generate profile summary
        summary = self._generate_profile_summary(trading_style, risk_profile, stats)

        return {
            "has_profile": True,
            "wallet": wallet_address,
            "trading_style": trading_style,
            "risk_profile": risk_profile,
            "success_indicators": success_indicators,
            "statistics": stats,
            "summary": summary
        }

    def _classify_trading_style(
        self,
        history: List[Dict],
        stats: Dict
    ) -> Dict[str, Any]:
        """Classify wallet's trading style"""
        tx_count = stats.get("transaction_count", 0)
        avg_value = stats.get("avg_value", 0)

        # Determine frequency
        if tx_count > 100:
            frequency = "very_high"
        elif tx_count > 30:
            frequency = "high"
        elif tx_count > 10:
            frequency = "moderate"
        else:
            frequency = "low"

        # Determine size preference
        if avg_value > 1000:
            size_preference = "large"
        elif avg_value > 100:
            size_preference = "medium"
        else:
            size_preference = "small"

        # Classify style
        if frequency == "very_high" and size_preference in ["medium", "large"]:
            style = "market_maker"
        elif frequency in ["high", "very_high"] and size_preference == "small":
            style = "active_trader"
        elif frequency in ["low", "moderate"] and size_preference == "large":
            style = "whale"
        elif frequency == "moderate" and size_preference == "medium":
            style = "regular_trader"
        else:
            style = "casual_user"

        return {
            "style": style,
            "frequency": frequency,
            "size_preference": size_preference,
            "confidence": 0.7 if tx_count > 20 else 0.5
        }

    def _determine_risk_profile(
        self,
        history: List[Dict],
        stats: Dict
    ) -> Dict[str, Any]:
        """Determine wallet's risk profile"""
        values = [tx.get("value_eth", 0) for tx in history]

        if not values:
            return {"profile": "unknown", "confidence": 0.0}

        avg_value = sum(values) / len(values)
        max_value = max(values)

        # Calculate risk indicators
        max_to_avg_ratio = max_value / avg_value if avg_value > 0 else 0

        # Classify risk
        if max_to_avg_ratio > 5:
            risk_level = "high"
        elif max_to_avg_ratio > 2:
            risk_level = "moderate"
        else:
            risk_level = "conservative"

        return {
            "profile": risk_level,
            "max_to_avg_ratio": round(max_to_avg_ratio, 2),
            "confidence": 0.7
        }

    def _analyze_success_indicators(self, history: List[Dict]) -> Dict[str, Any]:
        """Analyze indicators of successful trading"""
        # This is simplified - in production you'd track actual P&L
        indicators = {
            "activity_consistency": self._measure_consistency(history),
            "position_sizing": self._analyze_position_sizing(history)
        }

        return indicators

    def _measure_consistency(self, history: List[Dict]) -> str:
        """Measure consistency of activity"""
        if len(history) < 5:
            return "insufficient_data"

        values = [tx.get("value_eth", 0) for tx in history]
        avg = sum(values) / len(values) if values else 0

        if avg == 0:
            return "no_value_data"

        # Calculate coefficient of variation
        variance = sum((v - avg) ** 2 for v in values) / len(values)
        std_dev = variance ** 0.5
        cv = std_dev / avg if avg > 0 else 0

        if cv < 0.3:
            return "very_consistent"
        elif cv < 0.7:
            return "moderately_consistent"
        else:
            return "inconsistent"

    def _analyze_position_sizing(self, history: List[Dict]) -> str:
        """Analyze position sizing discipline"""
        values = [tx.get("value_eth", 0) for tx in history if tx.get("value_eth", 0) > 0]

        if len(values) < 3:
            return "insufficient_data"

        # Check if position sizes are disciplined (similar)
        avg = sum(values) / len(values)
        within_range = sum(1 for v in values if 0.5 * avg <= v <= 2 * avg)
        discipline_ratio = within_range / len(values)

        if discipline_ratio > 0.8:
            return "disciplined"
        elif discipline_ratio > 0.5:
            return "moderate"
        else:
            return "undisciplined"

    def _generate_profile_summary(
        self,
        trading_style: Dict,
        risk_profile: Dict,
        stats: Dict
    ) -> str:
        """Generate human-readable profile summary"""
        style = trading_style.get("style", "unknown")
        risk = risk_profile.get("profile", "unknown")
        tx_count = stats.get("transaction_count", 0)
        avg_value = stats.get("avg_value", 0)

        parts = [
            f"Type: {style}",
            f"Risk: {risk}",
            f"Txs: {tx_count}",
            f"Avg: {avg_value:.2f} ETH"
        ]

        return " | ".join(parts)
