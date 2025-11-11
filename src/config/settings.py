"""
Application settings and configuration
"""
import os
import sys

try:
    from dotenv import load_dotenv
    # Load environment variables from .env file
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not properly imported. Using manual .env loading as fallback.")
    # Manual .env loading as fallback
    try:
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip().strip('"\'')
    except FileNotFoundError:
        print("Warning: .env file not found. Using default values.")

# API Keys
# Etherscan API V2: Single API key works across all supported chains
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
# Deprecated: ARBISCAN_API_KEY is no longer needed with Etherscan API V2
# The single ETHERSCAN_API_KEY now works for all chains including Arbitrum
ARBISCAN_API_KEY = os.getenv("ARBISCAN_API_KEY")  # Kept for backward compatibility
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Blockchain RPC endpoints
ETHEREUM_RPC_URL = os.getenv("ETHEREUM_RPC_URL", "https://mainnet.infura.io/v3/YOUR_INFURA_KEY")
ARBITRUM_RPC_URL = os.getenv("ARBITRUM_RPC_URL", "https://arbitrum-mainnet.infura.io/v3/YOUR_INFURA_KEY")

# Database settings
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "whale_tracker")

# Application settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
TRANSACTION_THRESHOLD = float(os.getenv("TRANSACTION_THRESHOLD", "100"))  # in ETH
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "60"))  # in seconds
