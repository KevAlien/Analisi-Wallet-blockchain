#!/usr/bin/env python3
"""
Crypto Trading Bot - Main Entry Point

Automated cryptocurrency trading bot that combines:
- On-chain whale tracking signals
- Technical analysis strategies
- AI-powered decision making
- Risk management
- Automated trade execution

Usage:
    python trading_bot_main.py

    # With custom config
    python trading_bot_main.py --config custom_config.env

    # Dry run mode (no actual trades)
    python trading_bot_main.py --dry-run
"""
import os
import sys
import asyncio
import logging
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.orchestration.trading_bot import TradingBot


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def load_configuration(config_file: str = '.env') -> dict:
    """
    Load configuration from environment variables.

    Args:
        config_file: Path to .env file (default: '.env')

    Returns:
        Configuration dictionary
    """
    # Load environment variables
    load_dotenv(config_file)

    config = {
        # Trading Configuration
        'TRADING_SYMBOLS': os.getenv('TRADING_SYMBOLS', 'BTCUSDT,ETHUSDT').split(','),
        'TIMEFRAME': os.getenv('TRADING_TIMEFRAME', '15m'),
        'CHECK_INTERVAL_SECONDS': os.getenv('CHECK_INTERVAL_SECONDS', '60'),

        # Enabled Strategies
        'ENABLED_STRATEGIES': os.getenv(
            'ENABLED_STRATEGIES',
            'EMA_CROSSOVER,RSI_DIVERGENCE,SCALPING_TRIPLE,DIVERGENCE_DETECTOR'
        ).split(','),

        # Risk Management
        'INITIAL_CAPITAL': os.getenv('INITIAL_CAPITAL', '10000'),
        'RISK_PER_TRADE_PCT': os.getenv('RISK_PER_TRADE_PCT', '1.0'),
        'MAX_OPEN_POSITIONS': os.getenv('MAX_OPEN_POSITIONS', '3'),
        'MAX_RISK_PCT': os.getenv('MAX_RISK_PCT', '20.0'),

        # Data Sources
        'PRICE_SOURCE': os.getenv('PRICE_SOURCE', 'BINANCE'),

        # Notifications
        'TELEGRAM_BOT_TOKEN': os.getenv('TELEGRAM_BOT_TOKEN'),
        'TELEGRAM_CHAT_ID': os.getenv('TELEGRAM_CHAT_ID'),

        # AI Reasoning (optional)
        'ENABLE_AI_REASONING': os.getenv('ENABLE_AI_REASONING', 'false').lower() == 'true',
        'LLM_PROVIDER': os.getenv('LLM_PROVIDER', 'ollama'),
    }

    return config


def validate_configuration(config: dict) -> bool:
    """
    Validate configuration.

    Args:
        config: Configuration dictionary

    Returns:
        True if valid, raises ValueError otherwise
    """
    # Required fields
    required_fields = ['TRADING_SYMBOLS', 'INITIAL_CAPITAL']

    for field in required_fields:
        if field not in config or not config[field]:
            raise ValueError(f"Missing required configuration: {field}")

    # Validate initial capital
    try:
        capital = float(config['INITIAL_CAPITAL'])
        if capital <= 0:
            raise ValueError("INITIAL_CAPITAL must be positive")
    except ValueError:
        raise ValueError("INITIAL_CAPITAL must be a valid number")

    # Validate risk percentages
    try:
        risk = float(config['RISK_PER_TRADE_PCT'])
        if not 0 < risk <= 10:
            raise ValueError("RISK_PER_TRADE_PCT must be between 0 and 10")
    except ValueError:
        raise ValueError("RISK_PER_TRADE_PCT must be a valid number")

    logger.info("Configuration validated successfully")
    return True


async def main(args):
    """Main entry point for the trading bot."""
    try:
        # Load configuration
        config_file = args.config if args.config else '.env'
        logger.info(f"Loading configuration from {config_file}")

        config = load_configuration(config_file)

        # Validate configuration
        validate_configuration(config)

        # Display configuration
        logger.info("=" * 60)
        logger.info("TRADING BOT CONFIGURATION")
        logger.info("=" * 60)
        logger.info(f"Trading Symbols: {', '.join(config['TRADING_SYMBOLS'])}")
        logger.info(f"Timeframe: {config['TIMEFRAME']}")
        logger.info(f"Initial Capital: ${config['INITIAL_CAPITAL']}")
        logger.info(f"Risk per Trade: {config['RISK_PER_TRADE_PCT']}%")
        logger.info(f"Max Open Positions: {config['MAX_OPEN_POSITIONS']}")
        logger.info(f"Enabled Strategies: {', '.join(config['ENABLED_STRATEGIES'])}")
        logger.info(f"Price Source: {config['PRICE_SOURCE']}")
        logger.info(f"Dry Run Mode: {args.dry_run}")
        logger.info("=" * 60)

        if args.dry_run:
            logger.warning("⚠️  DRY RUN MODE - No actual trades will be executed")

        # Create and start trading bot
        logger.info("Initializing trading bot...")
        bot = TradingBot(config)

        logger.info("Starting trading bot...")
        logger.info("Press Ctrl+C to stop")

        await bot.start()

    except KeyboardInterrupt:
        logger.info("\nTrading bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Automated Cryptocurrency Trading Bot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python trading_bot_main.py                     # Run with default .env
  python trading_bot_main.py --config prod.env   # Run with custom config
  python trading_bot_main.py --dry-run           # Test mode (no trades)

For more information, see README.md
        """
    )

    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file (default: .env)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode - analyze signals but do not execute trades'
    )

    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )

    args = parser.parse_args()

    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    # Run the bot
    asyncio.run(main(args))
