"""
Historical pattern analyzer
Analyzes past behavior of wallets to identify patterns
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
from collections import Counter

logger = logging.getLogger(__name__)


class HistoricalPatternAnalyzer:
    """
    Analyzes historical transaction patterns for wallets

    Identifies:
    - Transaction frequency patterns
    - Time-of-day preferences
    - Value patterns (typical amounts)
    - Behavioral anomalies
    """

    def __init__(self, context_memory):
        """
        Initialize analyzer

        Args:
            context_memory: ContextMemory instance
        """
        self.memory = context_memory

    async def analyze_wallet(self, wallet_address: str) -> Dict[str, Any]:
        """
        Analyze historical patterns for a wallet

        Args:
            wallet_address: Wallet address to analyze

        Returns:
            Analysis results dict
        """
        history = self.memory.get_wallet_history(wallet_address, hours=24 * 7)  # Last week

        if not history:
            return {
                "has_history": False,
                "message": "No historical data available"
            }

        # Basic statistics
        stats = self.memory.get_wallet_statistics(wallet_address)

        # Analyze transaction frequency
        frequency = self._analyze_frequency(history)

        # Analyze time patterns
        time_patterns = self._analyze_time_patterns(history)

        # Analyze value patterns
        value_patterns = self._analyze_value_patterns(history)

        # Detect anomalies
        anomalies = self._detect_anomalies(history, stats)

        return {
            "has_history": True,
            "statistics": stats,
            "frequency": frequency,
            "time_patterns": time_patterns,
            "value_patterns": value_patterns,
            "anomalies": anomalies,
            "summary": self._generate_summary(stats, frequency, anomalies)
        }

    def _analyze_frequency(self, history: List[Dict]) -> Dict[str, Any]:
        """Analyze transaction frequency"""
        if len(history) < 2:
            return {"avg_per_day": 0, "pattern": "insufficient_data"}

        # Calculate daily transaction count
        dates = [tx.get("timestamp") for tx in history if tx.get("timestamp")]
        if not dates:
            return {"avg_per_day": 0, "pattern": "no_timestamps"}

        date_counts = Counter([d.date() for d in dates if isinstance(d, datetime)])
        avg_per_day = sum(date_counts.values()) / len(date_counts) if date_counts else 0

        # Determine pattern
        if avg_per_day > 10:
            pattern = "very_active"
        elif avg_per_day > 3:
            pattern = "active"
        elif avg_per_day > 0.5:
            pattern = "moderate"
        else:
            pattern = "low_activity"

        return {
            "avg_per_day": round(avg_per_day, 2),
            "pattern": pattern,
            "total_days": len(date_counts)
        }

    def _analyze_time_patterns(self, history: List[Dict]) -> Dict[str, Any]:
        """Analyze time-of-day patterns"""
        timestamps = [tx.get("timestamp") for tx in history if isinstance(tx.get("timestamp"), datetime)]

        if not timestamps:
            return {"pattern": "no_data"}

        # Group by hour
        hours = [ts.hour for ts in timestamps]
        hour_counts = Counter(hours)

        # Find most active hours
        most_active = hour_counts.most_common(3)

        # Determine if activity is concentrated
        top_hour_pct = (most_active[0][1] / len(hours) * 100) if most_active else 0

        pattern = "concentrated" if top_hour_pct > 30 else "distributed"

        return {
            "pattern": pattern,
            "most_active_hours": [h for h, _ in most_active],
            "concentration": f"{top_hour_pct:.1f}%"
        }

    def _analyze_value_patterns(self, history: List[Dict]) -> Dict[str, Any]:
        """Analyze transaction value patterns"""
        values = [tx.get("value_eth", 0) for tx in history if tx.get("value_eth", 0) > 0]

        if not values:
            return {"pattern": "no_data"}

        avg_value = sum(values) / len(values)
        max_value = max(values)
        min_value = min(values)

        # Calculate standard deviation
        variance = sum((v - avg_value) ** 2 for v in values) / len(values)
        std_dev = variance ** 0.5

        # Determine consistency
        coefficient_of_variation = (std_dev / avg_value) if avg_value > 0 else 0

        if coefficient_of_variation < 0.3:
            pattern = "consistent"
        elif coefficient_of_variation < 0.7:
            pattern = "moderate_variation"
        else:
            pattern = "high_variation"

        return {
            "pattern": pattern,
            "avg_value": round(avg_value, 2),
            "max_value": round(max_value, 2),
            "min_value": round(min_value, 2),
            "std_dev": round(std_dev, 2),
            "coefficient_of_variation": round(coefficient_of_variation, 2)
        }

    def _detect_anomalies(self, history: List[Dict], stats: Dict) -> List[str]:
        """Detect anomalous behaviors"""
        anomalies = []

        if not history:
            return anomalies

        # Check for sudden increase in activity
        recent = [tx for tx in history if self._is_recent(tx.get("timestamp"), hours=2)]
        if len(recent) > 5:
            anomalies.append("sudden_activity_spike")

        # Check for unusually large transaction
        values = [tx.get("value_eth", 0) for tx in history]
        if values:
            avg_value = sum(values) / len(values)
            max_value = max(values)
            if max_value > avg_value * 3:
                anomalies.append("unusually_large_transaction")

        # Check for dormant wallet becoming active
        if stats.get("transaction_count", 0) == 1:
            anomalies.append("first_transaction")

        return anomalies

    def _is_recent(self, timestamp: Optional[datetime], hours: int) -> bool:
        """Check if timestamp is within last N hours"""
        if not isinstance(timestamp, datetime):
            return False
        return timestamp >= datetime.now() - timedelta(hours=hours)

    def _generate_summary(self, stats: Dict, frequency: Dict, anomalies: List[str]) -> str:
        """Generate human-readable summary"""
        parts = []

        # Activity level
        pattern = frequency.get("pattern", "unknown")
        parts.append(f"Activity: {pattern}")

        # Value
        if stats.get("avg_value", 0) > 0:
            parts.append(f"Avg value: {stats['avg_value']:.2f} ETH")

        # Anomalies
        if anomalies:
            parts.append(f"Anomalies: {', '.join(anomalies)}")

        return " | ".join(parts)
