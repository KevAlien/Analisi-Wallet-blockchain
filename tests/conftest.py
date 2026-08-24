"""
Pytest configuration and fixtures for testing

This module provides shared fixtures and test utilities for the blockchain
wallet analysis test suite. Fixtures are organized by category:
- Environment setup (mock_env_vars)
- Basic data (sample_transaction, sample_whale_address, etc.)
- Analyzed transactions (for testing signal generation)
- Mock objects (mock_telegram_bot, mock_blockchain_client)
- Helper utilities (assert_signal_valid, create_test_transaction)
"""
import pytest
import os
from datetime import datetime
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any


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


# ============================================================================
# Test Helper Functions
# ============================================================================

def create_test_transaction(
    value_eth: float = 100.0,
    direction: str = "incoming",
    whale_address: str = "0x1234567890abcdef1234567890abcdef12345678",
    is_significant: bool = True,
    **kwargs
) -> Dict[str, Any]:
    """
    Helper function to create test transaction with custom parameters.

    Args:
        value_eth: Transaction value in ETH
        direction: "incoming", "outgoing", or "internal"
        whale_address: Address of the whale wallet
        is_significant: Whether transaction meets significance threshold
        **kwargs: Additional fields to override

    Returns:
        Dictionary with transaction data

    Example:
        >>> tx = create_test_transaction(value_eth=500, direction="outgoing")
        >>> assert tx['value_eth'] == 500
    """
    base_tx = {
        "hash": kwargs.get("hash", "0x" + "a" * 64),
        "from": kwargs.get("from", "0x" + "b" * 40),
        "to": kwargs.get("to", whale_address if direction == "incoming" else "0x" + "c" * 40),
        "value": str(int(value_eth * 10**18)),
        "blockNumber": kwargs.get("blockNumber", "12345678"),
        "timeStamp": kwargs.get("timeStamp", str(int(datetime.now().timestamp()))),
        "chain": kwargs.get("chain", "ethereum"),
        "value_eth": value_eth,
        "is_significant": is_significant,
        "direction": direction,
        "transaction_type": kwargs.get("transaction_type", "transfer"),
        "type_confidence": kwargs.get("type_confidence", 0.9),
        "threshold_used": kwargs.get("threshold_used", 100.0),
    }

    # Add wallet info based on direction
    if direction == "incoming":
        base_tx["from_wallet_info"] = None
        base_tx["to_wallet_info"] = {
            "address": whale_address,
            "name": "Test Whale",
            "category": "whale",
            "tags": ["test"]
        }
    elif direction == "outgoing":
        base_tx["from_wallet_info"] = {
            "address": whale_address,
            "name": "Test Whale",
            "category": "whale",
            "tags": ["test"]
        }
        base_tx["to_wallet_info"] = None
    else:  # internal
        base_tx["from_wallet_info"] = {
            "address": whale_address,
            "name": "Test Whale",
            "category": "whale",
            "tags": ["test"]
        }
        base_tx["to_wallet_info"] = {
            "address": kwargs.get("to", "0x" + "c" * 40),
            "name": "Test Whale 2",
            "category": "whale",
            "tags": ["test"]
        }

    # Apply any additional overrides
    base_tx.update(kwargs)
    return base_tx


def assert_signal_valid(signal, expected_type=None, min_value=None):
    """
    Helper function to validate signal object has required properties.

    Args:
        signal: Signal object to validate
        expected_type: Expected SignalType (optional)
        min_value: Minimum expected value in ETH (optional)

    Raises:
        AssertionError: If signal is invalid

    Example:
        >>> assert_signal_valid(signal, SignalType.ACCUMULATION, min_value=100)
    """
    # Check required fields
    assert signal is not None, "Signal is None"
    assert hasattr(signal, 'signal_type'), "Signal missing signal_type"
    assert hasattr(signal, 'strength'), "Signal missing strength"
    assert hasattr(signal, 'transaction_hash'), "Signal missing transaction_hash"
    assert hasattr(signal, 'wallet_address'), "Signal missing wallet_address"
    assert hasattr(signal, 'chain'), "Signal missing chain"
    assert hasattr(signal, 'value_eth'), "Signal missing value_eth"
    assert hasattr(signal, 'timestamp'), "Signal missing timestamp"

    # Check optional conditions
    if expected_type is not None:
        assert signal.signal_type == expected_type, \
            f"Expected signal type {expected_type}, got {signal.signal_type}"

    if min_value is not None:
        assert signal.value_eth >= min_value, \
            f"Expected value >= {min_value} ETH, got {signal.value_eth} ETH"

    # Validate data types
    assert isinstance(signal.value_eth, (int, float)), "value_eth must be numeric"
    assert signal.value_eth >= 0, "value_eth cannot be negative"
    assert signal.transaction_hash.startswith('0x'), "Invalid transaction hash format"
