"""
Main entry point for the Blockchain Wallet Analysis application
"""
import asyncio
import logging
import time
from typing import List, Dict, Any
import argparse
import os
from datetime import datetime

from src.config.settings import POLLING_INTERVAL
from src.config.wallet_registry import ALL_WALLETS, Chain
from src.config.llm_config import LLMConfig
from src.fetching.blockchain_client import BlockchainClient
from src.fetching.explorer_api import ExplorerAPIClient
from src.analysis.transaction_analyzer import TransactionAnalyzer
from src.signals.signal_generator import SignalGenerator, Signal, SignalType, SignalStrength
from src.signals.enhanced_signal import EnhancedSignal, create_signal_from_analysis
from src.notifications.telegram_bot import TelegramNotifier
from src.reasoning.agent_orchestrator import ReasoningAgentOrchestrator
from src.database import init_db, save_signal, is_tx_processed, mark_tx_processed, cleanup_old_transactions

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('whale_tracker.log')
    ]
)

logger = logging.getLogger(__name__)

class WhaleTracker:
    """Main application class that coordinates all components"""
    
    def __init__(self):
        """Initialize the application components"""
        self.blockchain_client = BlockchainClient()
        self.explorer_client = ExplorerAPIClient()
        self.transaction_analyzer = TransactionAnalyzer()
        self.signal_generator = SignalGenerator()
        self.telegram_notifier = TelegramNotifier()

        # Initialize AI reasoning agent
        try:
            self.llm_config = LLMConfig()
            self.reasoning_agent = ReasoningAgentOrchestrator(self.llm_config)
            logger.info("✅ AI Reasoning Agent initialized")
        except Exception as e:
            logger.warning(f"⚠️ AI Reasoning Agent not available: {str(e)}")
            self.reasoning_agent = None

        # Track the latest processed block for each chain
        self.last_processed_blocks: Dict[Chain, int] = {}

        # Inizializza DB SQLite locale (crea file e schema se non esistono)
        init_db()
    
    async def initialize(self):
        """Initialize all components"""
        logger.info("Initializing SentryCage application")

        # Initialize Telegram bot
        try:
            await self.telegram_notifier.initialize()
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {str(e)}")

        # Get latest block numbers
        for chain in Chain:
            try:
                latest_block = self.blockchain_client.get_latest_block_number(chain)
                # Start from 100 blocks before latest to catch recent transactions
                self.last_processed_blocks[chain] = max(0, latest_block - 100)
                logger.info(f"Starting from block {self.last_processed_blocks[chain]} on {chain.value}")
            except Exception as e:
                logger.error(f"Failed to get latest block for {chain.value}: {str(e)}")
                self.last_processed_blocks[chain] = 0

        self._log_startup_banner()

    def _log_startup_banner(self):
        """Print a clean summary of what the tracker is watching at startup."""
        active_chains = [c.value for c in Chain]
        telegram_status = "connected" if self.telegram_notifier.enabled else "disabled (no token)"
        ai_status = "on" if self.reasoning_agent else "off (rule-based)"

        lines = [
            "──────────────────────────────────────────────",
            "  🐋  SentryCage — whale tracker is live",
            "──────────────────────────────────────────────",
            f"  Wallets   : {len(ALL_WALLETS)} tracked",
            f"  Chains    : {', '.join(active_chains) or 'none configured'}",
            f"  AI reason : {ai_status}",
            f"  Telegram  : {telegram_status}",
            f"  Poll every: {POLLING_INTERVAL}s",
            "──────────────────────────────────────────────",
        ]
        logger.info("\n" + "\n".join(lines))
    
    async def run_forever(self):
        """Main application loop"""
        await self.initialize()
        
        logger.info("SentryCage is running")

        while True:
            try:
                await self.process_new_transactions()

                next_check = datetime.now().strftime("%H:%M:%S")
                logger.info(f"💤 Cycle complete · next check in {POLLING_INTERVAL}s (last at {next_check})")
                await asyncio.sleep(POLLING_INTERVAL)
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                await asyncio.sleep(10)
    
    async def process_new_transactions(self):
        """Process new transactions for all wallets"""
        for chain in Chain:
            try:
                # Get current block number
                current_block = self.blockchain_client.get_latest_block_number(chain)
                last_block = self.last_processed_blocks.get(chain, 0)

                if current_block <= last_block:
                    logger.info(f"No new blocks on {chain.value}")
                    continue

                logger.info(f"Processing blocks {last_block+1} to {current_block} on {chain.value}")

                # Process each wallet
                for wallet in ALL_WALLETS:
                    if chain not in wallet.chains:
                        continue

                    await self.process_wallet_transactions(wallet.address, chain, last_block + 1, current_block)

                # Update last processed block
                self.last_processed_blocks[chain] = current_block

            except Exception as e:
                logger.error(f"Error processing chain {chain.value}: {str(e)}")
    
    async def process_wallet_transactions(self, address: str, chain: Chain, from_block: int, to_block: int):
        """
        Process transactions for a specific wallet
        
        Args:
            address: Wallet address
            chain: Blockchain
            from_block: Starting block
            to_block: Ending block
        """
        try:
            # Get transactions from explorer API (more efficient than direct blockchain)
            transactions = self.explorer_client.get_wallet_transactions(
                address=address,
                chain=chain,
                start_block=from_block,
                end_block=to_block
            )
            
            if not transactions:
                return
                
            logger.info(f"Found {len(transactions)} transactions for {address[:8]}...{address[-6:]} on {chain.value}")
            
            # Collect transactions for batch processing
            batch_transactions = []

            for tx in transactions:
                # Deduplication persistente via SQLite (rimpiazza processed_txs set in-memory)
                tx_hash = tx.get("hash", "")
                if is_tx_processed(tx_hash, chain.value):
                    continue
                mark_tx_processed(tx_hash, chain.value, wallet_address=address)

                # Add chain information
                tx["chain"] = chain.value

                # Analyze the transaction (for baseline)
                analyzed_tx = self.transaction_analyzer.analyze_transaction(tx)

                # Only process significant transactions
                if analyzed_tx.get("is_significant"):
                    batch_transactions.append(analyzed_tx)

            # Process batch with AI reasoning if available
            if batch_transactions:
                await self._process_transaction_batch(batch_transactions)
        
        except Exception as e:
            logger.error(f"Error processing wallet {address}: {str(e)}")

    async def _process_transaction_batch(self, transactions: List[Dict[str, Any]]):
        """
        Process a batch of transactions with AI reasoning

        Args:
            transactions: List of analyzed transactions
        """
        try:
            ai_available = self.reasoning_agent and self.llm_config.enable_reasoning

            if ai_available:
                logger.info(f"🤖 Using AI reasoning for {len(transactions)} transactions")

                # Get AI-enhanced signals
                enhanced_signals = await self.reasoning_agent.analyze_transactions(
                    transactions,
                    use_reasoning=True
                )

                # Convert to signal objects, save and send
                for signal_data in enhanced_signals:
                    signal = create_signal_from_analysis(signal_data, enable_reasoning=True)
                    logger.info(f"Generated AI signal: {signal.signal_type.value} (confidence: {signal.confidence:.2f})")
                    save_signal({**signal_data, "source": "ai_reasoning"})
                    await self.telegram_notifier.send_signal(signal)


            if not ai_available:
                # Fallback to rule-based signals
                logger.info(f"📋 Using rule-based analysis for {len(transactions)} transactions")

                for analyzed_tx in transactions:
                    signals = self.signal_generator.generate_signals(analyzed_tx)

                    for signal in signals:
                        strategy = signal.signal_type.value
                        tx_hash = analyzed_tx.get("hash", "unknown")

                        logger.info(f"Generated signal: {strategy} for tx {tx_hash[:8]}...")
                        save_signal({
                            "signal_type": strategy,
                            "source": "whale_tracker",
                            "strength": signal.strength.value,
                            "chain": analyzed_tx.get("chain"),
                            "wallet_address": analyzed_tx.get("from"),
                            "transaction_hash": tx_hash,
                            "value_eth": analyzed_tx.get("value_eth"),
                        })
                        await self.telegram_notifier.send_signal(signal)

        except Exception as e:
            logger.error(f"Error in batch processing: {str(e)}")
            # Fallback to rule-based on error
            for analyzed_tx in transactions:
                try:
                    signals = self.signal_generator.generate_signals(analyzed_tx)
                    for signal in signals:
                        await self.telegram_notifier.send_signal(signal)
                except Exception as signal_error:
                    logger.error(f"Error generating fallback signal: {str(signal_error)}")

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="SentryCage - Monitor whale wallet activities")
    parser.add_argument("--test", action="store_true", help="Run in test mode")
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Send a gallery of sample alerts to TEST_CHAT_ID to preview Telegram formatting",
    )
    args = parser.parse_args()

    if args.preview:
        await run_preview()
    elif args.test:
        await run_test()
    else:
        tracker = WhaleTracker()
        await tracker.run_forever()


def _sample_signals() -> List[Signal]:
    """Build a representative gallery of alerts covering each signal type + AI reasoning."""
    now = datetime.now()
    samples: List[Signal] = [
        Signal(
            signal_type=SignalType.ACCUMULATION,
            strength=SignalStrength.VERY_HIGH,
            transaction_hash="0x" + "ab" * 32,
            wallet_address="0x" + "cd" * 20,
            wallet_name="Whale #1",
            wallet_category="whale",
            chain="ethereum",
            value_eth=1234.5,
            description="Whale wallet accumulating 1234.50 ETH over 3 transactions",
            timestamp=now,
            confidence=0.9,
        ),
        Signal(
            signal_type=SignalType.DISTRIBUTION,
            strength=SignalStrength.HIGH,
            transaction_hash="0x" + "ef" * 32,
            wallet_address="0x" + "12" * 20,
            wallet_name=None,
            wallet_category="market_maker",
            chain="arbitrum",
            value_eth=800.0,
            description="Market maker distributing 800.00 ETH to multiple addresses",
            timestamp=now,
            confidence=0.75,
        ),
        EnhancedSignal(
            signal_type=SignalType.EXCHANGE_DEPOSIT,
            strength=SignalStrength.HIGH,
            transaction_hash="0x" + "11" * 32,
            wallet_address="0x" + "22" * 20,
            wallet_name="Smart Money",
            wallet_category="whale",
            chain="ethereum",
            value_eth=500.0,
            description="Large deposit to Binance — possible sell pressure",
            reasoning_chain=[
                "Wallet moved 500 ETH to a known Binance hot wallet",
                "No matching withdrawal in the last 24h",
            ],
            predicted_impact="bearish",
            recommended_actions=[
                "Watch ETH order book depth on major venues",
                "Check for follow-on deposits from related wallets",
            ],
            correlations=["2 other MM wallets deposited to CEX in the last hour"],
            timestamp=now,
            confidence=0.82,
        ),
    ]
    return samples


async def run_preview():
    """Send sample alerts to TEST_CHAT_ID so formatting can be reviewed without a live whale."""
    logger.info("Running in preview mode — sending sample alerts")

    telegram = TelegramNotifier()
    if not telegram.enabled:
        logger.error("TELEGRAM_BOT_TOKEN non configurato — impossibile inviare la preview.")
        return

    chat_id = os.environ.get("TEST_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID")
    if not chat_id:
        logger.error("Né TEST_CHAT_ID né TELEGRAM_CHAT_ID impostati — non so a chi inviare la preview.")
        return

    try:
        await telegram.initialize()
        for signal in _sample_signals():
            ok = await telegram.send_signal(signal, int(chat_id))
            logger.info("Preview alert '%s' inviato: %s", signal.signal_type.value, ok)
            await asyncio.sleep(0.3)
        logger.info("Preview completata — controlla Telegram.")
    except Exception as e:
        logger.error(f"Preview fallita: {str(e)}")

async def run_test():
    """Run a test to verify all components are working"""
    logger.info("Running in test mode")
    
    # Create test instances
    explorer_client = ExplorerAPIClient()
    analyzer = TransactionAnalyzer()
    signal_generator = SignalGenerator()
    telegram = TelegramNotifier()
    
    try:
        # Initialize Telegram bot
        await telegram.initialize()
        
        # Add test subscriber (would come from command line in real usage)
        test_chat_id = os.environ.get("TEST_CHAT_ID")
        if test_chat_id:
            telegram.add_subscriber(int(test_chat_id))
        
        # Test Telegram delivery
        test_signal = Signal(
            signal_type=SignalType.ACCUMULATION,
            strength=SignalStrength.VERY_HIGH,
            transaction_hash="0x0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            wallet_address="0x0123456789abcdef0123456789abcdef01234567",
            wallet_name="Test Whale",
            wallet_category="whale",
            chain="ethereum",
            value_eth=1000,
            description="TEST SIGNAL - Whale wallet accumulating 1000.00 ETH",
            timestamp=datetime.now(),
            confidence=0.9,
            tags=["test", "whale"]
        )
        
        if test_chat_id:
            success = await telegram.send_signal(test_signal, int(test_chat_id))
            logger.info(f"Test signal sent: {success}")
        else:
            logger.warning("No TEST_CHAT_ID set, skipping Telegram test")
            
        logger.info("Test completed successfully")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
