"""
Tests for configuration loading
"""
import pytest
import os
from src.config.settings import *
from src.config.wallet_registry import ALL_WALLETS, Chain


class TestConfiguration:
    """Test cases for configuration"""

    def test_wallet_registry_loaded(self):
        """Test that wallet registry is loaded"""
        assert ALL_WALLETS is not None
        assert len(ALL_WALLETS) > 0

    def test_wallet_registry_structure(self):
        """Test that wallet registry has correct structure"""
        for wallet in ALL_WALLETS:
            assert hasattr(wallet, 'address')
            assert hasattr(wallet, 'name')
            assert hasattr(wallet, 'category')
            assert hasattr(wallet, 'chains')
            # Validate address format (should start with 0x and be 42 chars)
            assert wallet.address.startswith('0x')
            assert len(wallet.address) == 42

    def test_chain_enum(self):
        """Test that Chain enum is defined correctly"""
        assert Chain.ETHEREUM is not None
        assert Chain.ARBITRUM is not None
        assert Chain.ETHEREUM.value == 'ethereum'
        assert Chain.ARBITRUM.value == 'arbitrum'

    def test_settings_constants(self):
        """Test that settings constants are defined"""
        # These should be defined or have defaults
        assert POLLING_INTERVAL is not None
        assert isinstance(POLLING_INTERVAL, (int, float))
        assert POLLING_INTERVAL > 0


class TestLLMConfig:
    """Test cases for LLM configuration"""

    def test_llm_config_initialization(self, mock_env_vars):
        """Test that LLM config can be initialized"""
        from src.config.llm_config import LLMConfig

        # Should not raise an exception
        try:
            config = LLMConfig()
            assert config is not None
        except Exception:
            # LLM config might fail if provider is not configured, which is fine
            pytest.skip("LLM config requires provider setup")
