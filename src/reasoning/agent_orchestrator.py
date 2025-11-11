"""
Reasoning Agent Orchestrator
Coordinates LLM reasoning with analysis tools
"""
import asyncio
import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from .llm_factory import LLMFactory
from .context_memory import ContextMemory
from .tools.historical_analyzer import HistoricalPatternAnalyzer
from .tools.cross_chain_correlator import CrossChainCorrelator
from .tools.market_context_fetcher import MarketContextFetcher
from .tools.wallet_profiler import WalletProfiler
from src.config.llm_config import LLMConfig
from src.analysis.transaction_analyzer import TransactionAnalyzer

logger = logging.getLogger(__name__)


class ReasoningAgentOrchestrator:
    """
    Orchestrates AI reasoning loop for transaction analysis

    Coordinates:
    - LLM provider
    - Analysis tools
    - Context memory
    - Fallback strategies
    """

    # System prompt for the reasoning agent
    SYSTEM_PROMPT = """You are an expert blockchain analyst specializing in whale tracking and market maker detection.

Your role:
1. Analyze blockchain transactions to identify significant patterns
2. Generate trading signals with detailed reasoning chains
3. Correlate multi-chain events and historical patterns
4. Provide actionable intelligence for traders

CONSTRAINTS:
- ALWAYS provide clear reasoning for every signal
- MUST correlate with historical patterns when available
- NEVER ignore transactions > 100 ETH
- MUST explain unusual patterns in detail
- Focus on ACTIONABLE insights

OUTPUT FORMAT:
Respond with a JSON object containing:
{
  "signals": [
    {
      "type": "accumulation|distribution|exchange_deposit|exchange_withdrawal|unusual_activity",
      "strength": "low|medium|high|very_high",
      "reasoning_chain": ["step 1", "step 2", "step 3"],
      "confidence": 0.0-1.0,
      "predicted_impact": "bullish|bearish|neutral",
      "recommended_actions": ["action 1", "action 2"]
    }
  ],
  "correlations": ["correlation 1", "correlation 2"],
  "market_context_relevance": "how current market conditions affect this analysis"
}
"""

    def __init__(self, config: Optional[LLMConfig] = None):
        """
        Initialize reasoning agent

        Args:
            config: LLM configuration
        """
        self.config = config or LLMConfig()

        # Initialize LLM provider (with fallback)
        try:
            self.llm = LLMFactory.create_provider(self.config, enable_fallback=True)
            logger.info(f"Reasoning agent initialized with {self.llm.get_provider_name()}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM provider: {str(e)}")
            self.llm = None

        # Initialize components
        self.memory = ContextMemory(max_size=100, retention_hours=24)
        self.fallback_analyzer = TransactionAnalyzer()

        # Initialize tools
        self.historical_analyzer = HistoricalPatternAnalyzer(self.memory)
        self.cross_chain_correlator = CrossChainCorrelator(self.memory)
        self.market_context = MarketContextFetcher()
        self.wallet_profiler = WalletProfiler(self.memory)

        # Circuit breaker
        self.consecutive_failures = 0
        self.max_failures = 3

    async def analyze_transactions(
        self,
        transactions: List[Dict[str, Any]],
        use_reasoning: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Analyze transactions with optional AI reasoning

        Args:
            transactions: List of transactions to analyze
            use_reasoning: If False, use rule-based fallback

        Returns:
            List of enhanced signals
        """
        if not use_reasoning or not self.llm or not self.config.enable_reasoning:
            logger.info("Using rule-based fallback analysis")
            return await self._fallback_analysis(transactions)

        # Circuit breaker check
        if self.consecutive_failures >= self.max_failures:
            logger.warning(f"Circuit breaker active ({self.consecutive_failures} failures)")
            return await self._fallback_analysis(transactions)

        try:
            # Run reasoning loop with timeout
            async with asyncio.timeout(self.config.reasoning_timeout):
                results = await self._reasoning_loop(transactions)
                self.consecutive_failures = 0  # Reset on success
                return results

        except asyncio.TimeoutError:
            logger.warning(f"Reasoning timeout after {self.config.reasoning_timeout}s")
            self.consecutive_failures += 1
            return await self._fallback_analysis(transactions)

        except Exception as e:
            logger.error(f"Reasoning error: {str(e)}")
            self.consecutive_failures += 1
            return await self._fallback_analysis(transactions)

    async def _reasoning_loop(
        self,
        transactions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Execute AI reasoning loop

        Args:
            transactions: Transactions to analyze

        Returns:
            Enhanced signals with reasoning
        """
        logger.info(f"Starting reasoning loop for {len(transactions)} transactions")

        # Step 1: Gather context using tools
        context = await self._gather_context(transactions)

        # Step 2: Build prompt for LLM
        prompt = self._build_analysis_prompt(transactions, context)

        # Step 3: Get LLM analysis
        try:
            response = await self.llm.generate_json(
                prompt=prompt,
                system_prompt=self.SYSTEM_PROMPT,
                schema=self._get_response_schema(),
                temperature=0.7,
                max_tokens=2000
            )

            analysis = response.get("parsed_json", {})

        except Exception as e:
            logger.error(f"LLM generation failed: {str(e)}")
            raise

        # Step 4: Convert to enhanced signals
        signals = self._convert_to_signals(analysis, transactions, context)

        # Step 5: Store in memory
        for signal in signals:
            self.memory.add_signal(signal)

        for tx in transactions:
            self.memory.add_transaction(tx)

        logger.info(f"Generated {len(signals)} enhanced signals")
        return signals

    async def _gather_context(
        self,
        transactions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Gather contextual information using tools

        Args:
            transactions: Transactions to analyze

        Returns:
            Context dict
        """
        context = {}

        try:
            # Get market context
            context["market"] = await self.market_context.get_context()

            # Find cross-chain correlations
            context["correlations"] = await self.cross_chain_correlator.find_correlations(
                transactions,
                time_window_minutes=60
            )

            # Analyze involved wallets
            wallets = set()
            for tx in transactions:
                if tx.get("from"):
                    wallets.add(tx["from"])
                if tx.get("to"):
                    wallets.add(tx["to"])

            wallet_profiles = {}
            for wallet in list(wallets)[:5]:  # Limit to 5 wallets
                try:
                    profile = await self.wallet_profiler.profile_wallet(wallet)
                    if profile.get("has_profile"):
                        wallet_profiles[wallet] = profile
                except Exception as e:
                    logger.warning(f"Failed to profile wallet {wallet}: {str(e)}")

            context["wallet_profiles"] = wallet_profiles

            # Get historical patterns
            historical = {}
            for wallet in list(wallets)[:5]:
                try:
                    history = await self.historical_analyzer.analyze_wallet(wallet)
                    if history.get("has_history"):
                        historical[wallet] = history
                except Exception as e:
                    logger.warning(f"Failed to analyze wallet history {wallet}: {str(e)}")

            context["historical"] = historical

        except Exception as e:
            logger.error(f"Error gathering context: {str(e)}")

        return context

    def _build_analysis_prompt(
        self,
        transactions: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> str:
        """
        Build prompt for LLM analysis

        Args:
            transactions: Transactions to analyze
            context: Contextual information

        Returns:
            Analysis prompt string
        """
        # Format transactions
        tx_summary = []
        for tx in transactions[:10]:  # Limit to 10 transactions
            tx_summary.append({
                "hash": tx.get("hash", "unknown")[:16] + "...",
                "from": tx.get("from", "unknown")[:16] + "...",
                "to": tx.get("to", "unknown")[:16] + "...",
                "value_eth": tx.get("value_eth", 0),
                "chain": tx.get("chain", "unknown"),
                "type": tx.get("transaction_type", "unknown")
            })

        prompt = f"""Analyze these blockchain transactions and generate trading signals.

TRANSACTIONS ({len(transactions)} total, showing first {len(tx_summary)}):
{json.dumps(tx_summary, indent=2)}

MARKET CONTEXT:
{json.dumps(context.get("market", {}), indent=2)}

CORRELATIONS DETECTED:
{json.dumps(context.get("correlations", []), indent=2)}

WALLET PROFILES:
{json.dumps({k: v.get("summary", "") for k, v in context.get("wallet_profiles", {}).items()}, indent=2)}

HISTORICAL PATTERNS:
{json.dumps({k: v.get("summary", "") for k, v in context.get("historical", {}).items()}, indent=2)}

Analyze these transactions and provide:
1. Actionable trading signals with detailed reasoning
2. Correlation analysis
3. Market context relevance
4. Predicted impact and recommended actions
"""

        return prompt

    def _get_response_schema(self) -> Dict[str, Any]:
        """Get JSON schema for LLM response"""
        return {
            "type": "object",
            "properties": {
                "signals": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "strength": {"type": "string"},
                            "reasoning_chain": {"type": "array", "items": {"type": "string"}},
                            "confidence": {"type": "number"},
                            "predicted_impact": {"type": "string"},
                            "recommended_actions": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                },
                "correlations": {"type": "array", "items": {"type": "string"}},
                "market_context_relevance": {"type": "string"}
            }
        }

    def _convert_to_signals(
        self,
        analysis: Dict[str, Any],
        transactions: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Convert LLM analysis to enhanced signal format

        Args:
            analysis: LLM analysis output
            transactions: Original transactions
            context: Context data

        Returns:
            List of enhanced signals
        """
        signals = []

        for signal_data in analysis.get("signals", []):
            # Match signal to transaction (simplified)
            tx = transactions[0] if transactions else {}

            signal = {
                "signal_type": signal_data.get("type", "unusual_activity"),
                "strength": signal_data.get("strength", "medium"),
                "transaction_hash": tx.get("hash", "unknown"),
                "wallet_address": tx.get("from", "unknown"),
                "chain": tx.get("chain", "ethereum"),
                "value_eth": tx.get("value_eth", 0),
                "reasoning_chain": signal_data.get("reasoning_chain", []),
                "confidence": signal_data.get("confidence", 0.5),
                "predicted_impact": signal_data.get("predicted_impact", "neutral"),
                "recommended_actions": signal_data.get("recommended_actions", []),
                "correlations": analysis.get("correlations", []),
                "market_context": context.get("market", {}),
                "timestamp": datetime.now().isoformat(),
                "source": "reasoning_agent"
            }

            signals.append(signal)

        return signals

    async def _fallback_analysis(
        self,
        transactions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Fallback to rule-based analysis

        Args:
            transactions: Transactions to analyze

        Returns:
            Basic signals without reasoning
        """
        logger.info("Using rule-based fallback")
        signals = []

        for tx in transactions:
            # Use existing TransactionAnalyzer
            analyzed = self.fallback_analyzer.analyze_transaction(tx)

            if analyzed.get("is_significant"):
                signal = {
                    "signal_type": "transfer",
                    "strength": "medium",
                    "transaction_hash": tx.get("hash", "unknown"),
                    "wallet_address": tx.get("from", "unknown"),
                    "chain": tx.get("chain", "ethereum"),
                    "value_eth": analyzed.get("value_eth", 0),
                    "reasoning_chain": ["Rule-based analysis: significant transaction detected"],
                    "confidence": 0.6,
                    "predicted_impact": "neutral",
                    "recommended_actions": ["Monitor for follow-up activity"],
                    "timestamp": datetime.now().isoformat(),
                    "source": "fallback_analyzer"
                }
                signals.append(signal)

        return signals

    async def close(self):
        """Cleanup resources"""
        if hasattr(self.llm, 'close'):
            await self.llm.close()
        await self.market_context.close()
