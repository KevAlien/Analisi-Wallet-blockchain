"""
Pytest configuration and fixtures for testing
"""
import pytest
import os
from datetime import datetime
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing"""
    monkeypatch.setenv("ETHERSCAN_API_KEY", "test_etherscan_key")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_telegram_token")
    monkeypatch.setenv("ETHEREUM_RPC_URL", "https://test.rpc.url")
    monkeypatch.setenv("ARBITRUM_RPC_URL", "https://test.arbitrum.rpc.url")
    monkeypatch.setenv("POLLING_INTERVAL", "60")
    monkeypatch.setenv("TRANSACTION_THRESHOLD", "100")


@pytest.fixture
def sample_transaction():
    """Sample transaction data for testing"""
    return {
        "hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        "from": "0xabcdef1234567890abcdef1234567890abcdef12",
        "to": "0x1234567890abcdef1234567890abcdef12345678",
        "value": "1000000000000000000",  # 1 ETH in wei
        "blockNumber": "12345678",
        "timeStamp": str(int(datetime.now().timestamp())),
        "gas": "21000",
        "gasPrice": "50000000000",
        "gasUsed": "21000",
        "isError": "0",
        "chain": "ethereum"
    }


@pytest.fixture
def sample_whale_address():
    """Sample whale wallet address"""
    return "0x1234567890abcdef1234567890abcdef12345678"


@pytest.fixture
def sample_exchange_address():
    """Sample exchange address (Binance hot wallet)"""
    return "0xdfd5293d8e347dfe59e90efd55b2956a1343963d"


@pytest.fixture
def mock_telegram_bot():
    """Mock Telegram bot for testing"""
    bot = AsyncMock()
    bot.send_message = AsyncMock(return_value=True)
    bot.get_me = AsyncMock(return_value={"username": "test_bot"})
    return bot


@pytest.fixture
def mock_blockchain_client():
    """Mock blockchain client"""
    client = Mock()
    client.get_latest_block_number = Mock(return_value=12345678)
    client.get_transaction = Mock(return_value={"hash": "0x123", "value": "1000000000000000000"})
    return client


@pytest.fixture
def sample_wallet_info():
    """Sample wallet info structure"""
    return {
        "address": "0x1234567890abcdef1234567890abcdef12345678",
        "name": "Test Whale",
        "category": "whale",
        "tags": ["test", "whale"]
    }


@pytest.fixture
def analyzed_accumulation_transaction(sample_whale_address):
    """Sample analyzed transaction for accumulation (incoming to whale)"""
    return {
        "hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        "from": "0xabcdef1234567890abcdef1234567890abcdef12",
        "to": sample_whale_address,
        "value": "500000000000000000000",  # 500 ETH in wei
        "blockNumber": "12345678",
        "timeStamp": str(int(datetime.now().timestamp())),
        "chain": "ethereum",
        "value_eth": 500.0,
        "is_significant": True,
        "direction": "incoming",
        "transaction_type": "transfer",
        "type_confidence": 0.9,
        "threshold_used": 100.0,
        "from_wallet_info": None,
        "to_wallet_info": {
            "address": sample_whale_address,
            "name": "Test Whale",
            "category": "whale",
            "tags": ["test", "whale"]
        }
    }


@pytest.fixture
def analyzed_distribution_transaction(sample_whale_address):
    """Sample analyzed transaction for distribution (outgoing from whale)"""
    return {
        "hash": "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "from": sample_whale_address,
        "to": "0xabcdef1234567890abcdef1234567890abcdef12",
        "value": "500000000000000000000",  # 500 ETH in wei
        "blockNumber": "12345679",
        "timeStamp": str(int(datetime.now().timestamp())),
        "chain": "ethereum",
        "value_eth": 500.0,
        "is_significant": True,
        "direction": "outgoing",
        "transaction_type": "transfer",
        "type_confidence": 0.9,
        "threshold_used": 100.0,
        "from_wallet_info": {
            "address": sample_whale_address,
            "name": "Test Whale",
            "category": "whale",
            "tags": ["test", "whale"]
        },
        "to_wallet_info": None
    }


@pytest.fixture
def analyzed_exchange_deposit_transaction(sample_whale_address, sample_exchange_address):
    """Sample analyzed transaction for exchange deposit"""
    return {
        "hash": "0xfedcba0987654321fedcba0987654321fedcba0987654321fedcba0987654321",
        "from": sample_whale_address,
        "to": sample_exchange_address,
        "value": "1000000000000000000000",  # 1000 ETH in wei
        "blockNumber": "12345680",
        "timeStamp": str(int(datetime.now().timestamp())),
        "chain": "ethereum",
        "value_eth": 1000.0,
        "is_significant": True,
        "direction": "outgoing",
        "transaction_type": "transfer",
        "type_confidence": 0.85,
        "threshold_used": 100.0,
        "from_wallet_info": {
            "address": sample_whale_address,
            "name": "Test Whale",
            "category": "whale",
            "tags": ["test", "whale"]
        },
        "to_wallet_info": None,
        "counterparty_category": "exchange"
    }
