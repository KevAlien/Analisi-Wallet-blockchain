"""
Context memory for reasoning agent
Stores recent events and patterns for contextual analysis
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import deque
import logging

logger = logging.getLogger(__name__)


class ContextMemory:
    """
    Circular buffer memory for storing recent blockchain events

    Keeps track of:
    - Recent transactions
    - Generated signals
    - Detected patterns
    - Market context snapshots
    """

    def __init__(self, max_size: int = 100, retention_hours: int = 24):
        """
        Initialize context memory

        Args:
            max_size: Maximum number of events to store
            retention_hours: How long to keep events (hours)
        """
        self.max_size = max_size
        self.retention_hours = retention_hours

        # Circular buffers
        self.transactions = deque(maxlen=max_size)
        self.signals = deque(maxlen=max_size)
        self.patterns = deque(maxlen=max_size)
        self.market_snapshots = deque(maxlen=50)

        # Wallet activity tracking
        self.wallet_activity: Dict[str, List[Dict]] = {}

        logger.info(f"Context memory initialized: size={max_size}, retention={retention_hours}h")

    def add_transaction(self, transaction: Dict[str, Any]):
        """
        Add transaction to memory

        Args:
            transaction: Transaction data
        """
        entry = {
            "timestamp": datetime.now(),
            "data": transaction,
            "type": "transaction"
        }
        self.transactions.append(entry)

        # Track by wallet
        wallet = transaction.get("from") or transaction.get("to")
        if wallet:
            if wallet not in self.wallet_activity:
                self.wallet_activity[wallet] = []
            self.wallet_activity[wallet].append(entry)

        self._cleanup_old_entries()

    def add_signal(self, signal: Dict[str, Any]):
        """
        Add generated signal to memory

        Args:
            signal: Signal data
        """
        entry = {
            "timestamp": datetime.now(),
            "data": signal,
            "type": "signal"
        }
        self.signals.append(entry)
        self._cleanup_old_entries()

    def add_pattern(self, pattern: Dict[str, Any]):
        """
        Add detected pattern to memory

        Args:
            pattern: Pattern data
        """
        entry = {
            "timestamp": datetime.now(),
            "data": pattern,
            "type": "pattern"
        }
        self.patterns.append(entry)
        self._cleanup_old_entries()

    def add_market_snapshot(self, snapshot: Dict[str, Any]):
        """
        Add market context snapshot

        Args:
            snapshot: Market data (price, volume, etc.)
        """
        entry = {
            "timestamp": datetime.now(),
            "data": snapshot
        }
        self.market_snapshots.append(entry)

    def get_recent_transactions(
        self,
        count: Optional[int] = None,
        wallet: Optional[str] = None,
        minutes: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent transactions

        Args:
            count: Max number to return
            wallet: Filter by wallet address
            minutes: Only return transactions from last N minutes

        Returns:
            List of transactions
        """
        transactions = list(self.transactions)

        # Filter by time
        if minutes:
            cutoff = datetime.now() - timedelta(minutes=minutes)
            transactions = [t for t in transactions if t["timestamp"] >= cutoff]

        # Filter by wallet
        if wallet:
            wallet = wallet.lower()
            transactions = [
                t for t in transactions
                if wallet in [
                    t["data"].get("from", "").lower(),
                    t["data"].get("to", "").lower()
                ]
            ]

        # Limit count
        if count:
            transactions = transactions[-count:]

        return [t["data"] for t in transactions]

    def get_recent_signals(self, count: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get recent signals"""
        signals = list(self.signals)
        if count:
            signals = signals[-count:]
        return [s["data"] for s in signals]

    def get_wallet_history(
        self,
        wallet: str,
        hours: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get transaction history for a wallet

        Args:
            wallet: Wallet address
            hours: Only return transactions from last N hours

        Returns:
            List of transactions
        """
        wallet = wallet.lower()
        history = self.wallet_activity.get(wallet, [])

        if hours:
            cutoff = datetime.now() - timedelta(hours=hours)
            history = [h for h in history if h["timestamp"] >= cutoff]

        return [h["data"] for h in history]

    def get_wallet_statistics(self, wallet: str) -> Dict[str, Any]:
        """
        Get statistics for a wallet

        Args:
            wallet: Wallet address

        Returns:
            Statistics dict
        """
        history = self.get_wallet_history(wallet)

        if not history:
            return {
                "transaction_count": 0,
                "first_seen": None,
                "last_seen": None,
                "total_value": 0
            }

        timestamps = [h.get("timestamp") for h in history if h.get("timestamp")]
        values = [h.get("value_eth", 0) for h in history]

        return {
            "transaction_count": len(history),
            "first_seen": min(timestamps) if timestamps else None,
            "last_seen": max(timestamps) if timestamps else None,
            "total_value": sum(values),
            "avg_value": sum(values) / len(values) if values else 0
        }

    def get_context_summary(self) -> Dict[str, Any]:
        """
        Get summary of current context

        Returns:
            Context summary dict
        """
        return {
            "transactions_count": len(self.transactions),
            "signals_count": len(self.signals),
            "patterns_count": len(self.patterns),
            "tracked_wallets": len(self.wallet_activity),
            "latest_market_snapshot": self.market_snapshots[-1]["data"] if self.market_snapshots else None,
            "memory_utilization": {
                "transactions": f"{len(self.transactions)}/{self.max_size}",
                "signals": f"{len(self.signals)}/{self.max_size}",
                "patterns": f"{len(self.patterns)}/{self.max_size}"
            }
        }

    def _cleanup_old_entries(self):
        """Remove entries older than retention period"""
        cutoff = datetime.now() - timedelta(hours=self.retention_hours)

        # Clean transactions
        while self.transactions and self.transactions[0]["timestamp"] < cutoff:
            self.transactions.popleft()

        # Clean signals
        while self.signals and self.signals[0]["timestamp"] < cutoff:
            self.signals.popleft()

        # Clean patterns
        while self.patterns and self.patterns[0]["timestamp"] < cutoff:
            self.patterns.popleft()

        # Clean wallet activity
        for wallet in list(self.wallet_activity.keys()):
            self.wallet_activity[wallet] = [
                entry for entry in self.wallet_activity[wallet]
                if entry["timestamp"] >= cutoff
            ]
            if not self.wallet_activity[wallet]:
                del self.wallet_activity[wallet]

    def clear(self):
        """Clear all memory"""
        self.transactions.clear()
        self.signals.clear()
        self.patterns.clear()
        self.market_snapshots.clear()
        self.wallet_activity.clear()
        logger.info("Context memory cleared")
