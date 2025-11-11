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
from src.signals.signal_generator import SignalGenerator, Signal
from src.signals.enhanced_signal import EnhancedSignal, create_signal_from_analysis
from src.notifications.telegram_bot import TelegramNotifier
from src.reasoning.agent_orchestrator import ReasoningAgentOrchestrator

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

        # Cache for processed transactions to avoid duplicates
        self.processed_txs = set()
    
    async def initialize(self):
        """Initialize all components"""
        logger.info("Initializing Whale Tracker application")
        
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
    
    async def run_forever(self):
        """Main application loop"""
        await self.initialize()
        
        logger.info("Whale Tracker is running")
        
        while True:
            try:
                await self.process_new_transactions()
                logger.info(f"Sleeping for {POLLING_INTERVAL} seconds")
                await asyncio.sleep(POLLING_INTERVAL)
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                await asyncio.sleep(10)  # Sleep and retry on error
    
    async def process_new_transactions(self):
        """Process new transactions for all wallets"""
        for chain in Chain:
            try:
                # Get current block number
                current_block = self.blockchain_client.get_latest_block_number(chain)
                last_block = self.last_processed_blocks[chain]
                
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
                # Skip already processed transactions
                tx_hash = tx.get("hash", "")
                if tx_hash in self.processed_txs:
                    continue

                # Mark as processed
                self.processed_txs.add(tx_hash)

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
            # Use AI reasoning if available
            if self.reasoning_agent and self.llm_config.enable_reasoning:
                logger.info(f"🤖 Using AI reasoning for {len(transactions)} transactions")

                # Get AI-enhanced signals
                enhanced_signals = await self.reasoning_agent.analyze_transactions(
                    transactions,
                    use_reasoning=True
                )

                # Convert to signal objects and send
                for signal_data in enhanced_signals:
                    signal = create_signal_from_analysis(signal_data, enable_reasoning=True)
                    logger.info(f"Generated AI signal: {signal.signal_type.value} (confidence: {signal.confidence:.2f})")
                    await self.telegram_notifier.send_signal(signal)

            else:
                # Fallback to rule-based signals
                logger.info(f"📋 Using rule-based analysis for {len(transactions)} transactions")

                for analyzed_tx in transactions:
                    signals = self.signal_generator.generate_signals(analyzed_tx)

                    for signal in signals:
                        tx_hash = analyzed_tx.get("hash", "unknown")
                        logger.info(f"Generated signal: {signal.signal_type.value} for tx {tx_hash[:8]}...")
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
    parser = argparse.ArgumentParser(description="Whale Tracker - Monitor whale wallet activities")
    parser.add_argument("--test", action="store_true", help="Run in test mode")
    args = parser.parse_args()
    
    if args.test:
        await run_test()
    else:
        tracker = WhaleTracker()
        await tracker.run_forever()

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
            signal_type=signal_generator._signal_type.__class__.ACCUMULATION,
            strength=signal_generator._determine_signal_strength(1000),
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
