"""
Cross-chain correlation analyzer
Identifies correlated events across different blockchains
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class CrossChainCorrelator:
    """
    Analyzes correlations between transactions across chains

    Identifies:
    - Coordinated movements across chains
    - Bridge-related patterns
    - Multi-chain whale operations
    """

    def __init__(self, context_memory):
        """
        Initialize correlator

        Args:
            context_memory: ContextMemory instance
        """
        self.memory = context_memory

    async def find_correlations(
        self,
        transactions: List[Dict[str, Any]],
        time_window_minutes: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Find correlated events across chains

        Args:
            transactions: List of transactions to analyze
            time_window_minutes: Time window for correlation (minutes)

        Returns:
            List of detected correlations
        """
        correlations = []

        # Get recent context from memory
        recent_txs = self.memory.get_recent_transactions(
            minutes=time_window_minutes,
            count=100
        )

        # Combine with current transactions
        all_txs = recent_txs + transactions

        # Group by chain
        by_chain = self._group_by_chain(all_txs)

        # Find temporal correlations
        temporal = self._find_temporal_correlations(by_chain, time_window_minutes)
        if temporal:
            correlations.extend(temporal)

        # Find wallet correlations
        wallet = self._find_wallet_correlations(by_chain, time_window_minutes)
        if wallet:
            correlations.extend(wallet)

        # Find value correlations
        value = self._find_value_correlations(by_chain, time_window_minutes)
        if value:
            correlations.extend(value)

        return correlations

    def _group_by_chain(self, transactions: List[Dict]) -> Dict[str, List[Dict]]:
        """Group transactions by chain"""
        by_chain = {}

        for tx in transactions:
            chain = tx.get("chain", "unknown")
            if chain not in by_chain:
                by_chain[chain] = []
            by_chain[chain].append(tx)

        return by_chain

    def _find_temporal_correlations(
        self,
        by_chain: Dict[str, List[Dict]],
        window_minutes: int
    ) -> List[Dict[str, Any]]:
        """Find transactions happening at similar times across chains"""
        correlations = []

        chains = list(by_chain.keys())
        if len(chains) < 2:
            return correlations

        # Compare each pair of chains
        for i in range(len(chains)):
            for j in range(i + 1, len(chains)):
                chain1, chain2 = chains[i], chains[j]
                txs1 = by_chain[chain1]
                txs2 = by_chain[chain2]

                # Find temporally close transactions
                for tx1 in txs1:
                    ts1 = tx1.get("timestamp")
                    if not isinstance(ts1, datetime):
                        continue

                    for tx2 in txs2:
                        ts2 = tx2.get("timestamp")
                        if not isinstance(ts2, datetime):
                            continue

                        # Check if within time window
                        time_diff = abs((ts2 - ts1).total_seconds() / 60)
                        if time_diff <= window_minutes:
                            correlations.append({
                                "type": "temporal",
                                "chains": [chain1, chain2],
                                "time_diff_minutes": round(time_diff, 2),
                                "transactions": [tx1.get("hash"), tx2.get("hash")],
                                "description": f"Activity on {chain1} and {chain2} within {time_diff:.1f} minutes"
                            })

        return correlations

    def _find_wallet_correlations(
        self,
        by_chain: Dict[str, List[Dict]],
        window_minutes: int
    ) -> List[Dict[str, Any]]:
        """Find same wallet active on multiple chains"""
        correlations = []

        # Track wallet activity by chain
        wallet_chains = {}

        for chain, txs in by_chain.items():
            for tx in txs:
                wallet = tx.get("from") or tx.get("to")
                if not wallet:
                    continue

                wallet = wallet.lower()
                if wallet not in wallet_chains:
                    wallet_chains[wallet] = {}

                if chain not in wallet_chains[wallet]:
                    wallet_chains[wallet][chain] = []

                wallet_chains[wallet][chain].append(tx)

        # Find wallets active on multiple chains
        for wallet, chains in wallet_chains.items():
            if len(chains) >= 2:
                correlations.append({
                    "type": "multi_chain_wallet",
                    "wallet": wallet,
                    "chains": list(chains.keys()),
                    "transaction_count": sum(len(txs) for txs in chains.values()),
                    "description": f"Wallet active on {len(chains)} chains: {', '.join(chains.keys())}"
                })

        return correlations

    def _find_value_correlations(
        self,
        by_chain: Dict[str, List[Dict]],
        window_minutes: int
    ) -> List[Dict[str, Any]]:
        """Find similar-value transactions across chains"""
        correlations = []

        chains = list(by_chain.keys())
        if len(chains) < 2:
            return correlations

        # Compare transactions with similar values
        for i in range(len(chains)):
            for j in range(i + 1, len(chains)):
                chain1, chain2 = chains[i], chains[j]
                txs1 = by_chain[chain1]
                txs2 = by_chain[chain2]

                for tx1 in txs1:
                    value1 = tx1.get("value_eth", 0)
                    if value1 < 10:  # Only significant amounts
                        continue

                    for tx2 in txs2:
                        value2 = tx2.get("value_eth", 0)
                        if value2 < 10:
                            continue

                        # Check if values are similar (within 5%)
                        diff_pct = abs(value1 - value2) / max(value1, value2) * 100
                        if diff_pct <= 5:
                            correlations.append({
                                "type": "similar_value",
                                "chains": [chain1, chain2],
                                "value_eth": round((value1 + value2) / 2, 2),
                                "transactions": [tx1.get("hash"), tx2.get("hash")],
                                "description": f"Similar value transactions: {value1:.2f} ETH on {chain1}, {value2:.2f} ETH on {chain2}"
                            })

        return correlations

    def analyze_bridge_activity(
        self,
        transactions: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Detect bridge-related activity patterns

        Args:
            transactions: Transactions to analyze

        Returns:
            Bridge activity analysis or None
        """
        # Common bridge contract addresses
        bridge_addresses = {
            "0x8484ef722627bf18ca5ae6bcf031c23e6e922b30": "Arbitrum Bridge",
            "0x4dbd4fc535ac27206064b68ffcf827b0a60bab3f": "Arbitrum Inbox",
            # Add more bridge addresses as needed
        }

        bridge_txs = []
        for tx in transactions:
            to_addr = tx.get("to", "").lower()
            if to_addr in bridge_addresses:
                bridge_txs.append({
                    "transaction": tx,
                    "bridge": bridge_addresses[to_addr]
                })

        if not bridge_txs:
            return None

        return {
            "detected": True,
            "bridge_count": len(bridge_txs),
            "bridges_used": list(set(b["bridge"] for b in bridge_txs)),
            "total_value": sum(tx["transaction"].get("value_eth", 0) for tx in bridge_txs),
            "description": f"Detected {len(bridge_txs)} bridge transactions"
        }
