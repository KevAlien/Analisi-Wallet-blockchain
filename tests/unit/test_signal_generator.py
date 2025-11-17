"""
Tests for signal generation functionality
"""
import pytest
from datetime import datetime
from src.signals.signal_generator import SignalGenerator, SignalType, SignalStrength


class TestSignalGenerator:
    """Test cases for SignalGenerator"""

    def setup_method(self):
        """Setup test fixtures"""
        self.signal_generator = SignalGenerator()

    def test_signal_generator_initialization(self):
        """Test that SignalGenerator initializes correctly"""
        assert self.signal_generator is not None
        assert hasattr(self.signal_generator, 'generate_signals')

    def test_generate_accumulation_signal(self, analyzed_accumulation_transaction):
        """Test generation of accumulation signal"""
        signals = self.signal_generator.generate_signals(analyzed_accumulation_transaction)

        assert len(signals) > 0
        # Check that at least one signal is accumulation type
        accumulation_signals = [s for s in signals if s.signal_type == SignalType.ACCUMULATION]
        assert len(accumulation_signals) > 0

        # Verify signal properties
        signal = accumulation_signals[0]
        assert signal.wallet_name == "Test Whale"
        assert signal.wallet_category == "whale"
        assert signal.value_eth == 500.0

    def test_generate_distribution_signal(self, analyzed_distribution_transaction):
        """Test generation of distribution signal"""
        signals = self.signal_generator.generate_signals(analyzed_distribution_transaction)

        assert len(signals) > 0
        # Check that at least one signal is distribution type
        distribution_signals = [s for s in signals if s.signal_type == SignalType.DISTRIBUTION]
        assert len(distribution_signals) > 0

        # Verify signal properties
        signal = distribution_signals[0]
        assert signal.wallet_name == "Test Whale"
        assert signal.wallet_category == "whale"
        assert signal.value_eth == 500.0

    def test_exchange_deposit_signal(self, analyzed_exchange_deposit_transaction):
        """Test generation of exchange deposit signal"""
        signals = self.signal_generator.generate_signals(analyzed_exchange_deposit_transaction)

        assert len(signals) > 0
        # Exchange deposits should generate exchange_deposit signals
        exchange_signals = [s for s in signals if s.signal_type == SignalType.EXCHANGE_DEPOSIT]
        assert len(exchange_signals) > 0

        # Verify signal properties
        signal = exchange_signals[0]
        assert signal.wallet_name == "Test Whale"
        assert signal.value_eth == 1000.0
        assert "exchange" in signal.tags

    def test_no_signals_for_insignificant_transaction(self, sample_transaction):
        """Test that insignificant transactions don't generate signals"""
        sample_transaction['is_significant'] = False
        sample_transaction['value_eth'] = 0.1

        signals = self.signal_generator.generate_signals(sample_transaction)

        # Should generate no signals or low strength signals
        assert len(signals) == 0 or all(s.strength == SignalStrength.LOW for s in signals)

    def test_signal_strength_calculation(self, analyzed_exchange_deposit_transaction):
        """Test that signal strength is calculated correctly based on value"""
        # 1000 ETH transaction should generate very high strength signal
        signals = self.signal_generator.generate_signals(analyzed_exchange_deposit_transaction)

        assert len(signals) > 0
        # Signal should have very high strength (1000+ ETH threshold)
        signal = signals[0]
        assert signal.strength == SignalStrength.VERY_HIGH
