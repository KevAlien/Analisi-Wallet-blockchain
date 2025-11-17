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
