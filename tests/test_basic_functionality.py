"""
Basic functionality tests to ensure the application can start and run
"""
import pytest
from unittest.mock import Mock, patch
import sys


class TestBasicFunctionality:
    """Basic smoke tests for the application"""

    def test_imports(self):
        """Test that all core modules can be imported"""
        try:
            from src.config.settings import POLLING_INTERVAL
            from src.config.wallet_registry import ALL_WALLETS, Chain
            from src.analysis.transaction_analyzer import TransactionAnalyzer
            from src.signals.signal_generator import SignalGenerator, SignalType, SignalStrength
            from src.fetching.blockchain_client import BlockchainClient
            from src.fetching.explorer_api import ExplorerAPIClient

            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import core modules: {e}")

    def test_wallet_registry_not_empty(self):
        """Test that wallet registry has wallets configured"""
        from src.config.wallet_registry import ALL_WALLETS

        assert len(ALL_WALLETS) > 0, "No wallets configured in registry"

    def test_transaction_analyzer_creation(self):
        """Test that TransactionAnalyzer can be instantiated"""
        from src.analysis.transaction_analyzer import TransactionAnalyzer

        analyzer = TransactionAnalyzer()
        assert analyzer is not None

    def test_signal_generator_creation(self):
        """Test that SignalGenerator can be instantiated"""
        from src.signals.signal_generator import SignalGenerator

        generator = SignalGenerator()
        assert generator is not None

    def test_blockchain_client_creation(self):
        """Test that BlockchainClient can be instantiated"""
        from src.fetching.blockchain_client import BlockchainClient

        try:
            client = BlockchainClient()
            assert client is not None
        except Exception as e:
            # Might fail without proper RPC URLs, which is acceptable
            pytest.skip(f"BlockchainClient requires RPC configuration: {e}")

    def test_explorer_api_creation(self):
        """Test that ExplorerAPIClient can be instantiated"""
        from src.fetching.explorer_api import ExplorerAPIClient

        try:
            client = ExplorerAPIClient()
            assert client is not None
        except Exception as e:
            # Might fail without API keys, which is acceptable
            pytest.skip(f"ExplorerAPIClient requires API keys: {e}")

    def test_signal_types_defined(self):
        """Test that signal types are properly defined"""
        from src.signals.signal_generator import SignalType, SignalStrength

        # Check that enums have expected values
        assert SignalType.ACCUMULATION is not None
        assert SignalType.DISTRIBUTION is not None
        assert SignalStrength.LOW is not None
        assert SignalStrength.HIGH is not None

    def test_chain_enum_defined(self):
        """Test that Chain enum is properly defined"""
        from src.config.wallet_registry import Chain

        assert Chain.ETHEREUM is not None
        assert Chain.ARBITRUM is not None
        assert hasattr(Chain.ETHEREUM, 'value')

    def test_main_module_imports(self):
        """Test that main module can be imported"""
        try:
            import main
            assert hasattr(main, 'WhaleTracker')
            assert hasattr(main, 'main')
            assert hasattr(main, 'run_test')
        except ImportError as e:
            pytest.fail(f"Failed to import main module: {e}")
