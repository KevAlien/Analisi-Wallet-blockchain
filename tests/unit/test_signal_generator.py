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

    def test_generate_accumulation_signal(self, sample_transaction, sample_whale_address):
        """Test generation of accumulation signal"""
        # Modify transaction to be an accumulation (incoming to whale)
        sample_transaction['to'] = sample_whale_address
        sample_transaction['is_significant'] = True
        sample_transaction['value_eth'] = 100.0
        sample_transaction['transaction_type'] = 'receive'

        signals = self.signal_generator.generate_signals(sample_transaction)

        assert len(signals) > 0
        # Check that at least one signal is accumulation type
        accumulation_signals = [s for s in signals if s.signal_type == SignalType.ACCUMULATION]
        assert len(accumulation_signals) > 0

    def test_generate_distribution_signal(self, sample_transaction, sample_whale_address):
        """Test generation of distribution signal"""
        # Modify transaction to be a distribution (outgoing from whale)
        sample_transaction['from'] = sample_whale_address
        sample_transaction['is_significant'] = True
        sample_transaction['value_eth'] = 100.0
        sample_transaction['transaction_type'] = 'send'

        signals = self.signal_generator.generate_signals(sample_transaction)

        assert len(signals) > 0
        # Check that at least one signal is distribution type
        distribution_signals = [s for s in signals if s.signal_type == SignalType.DISTRIBUTION]
        assert len(distribution_signals) > 0

    def test_exchange_deposit_signal(self, sample_transaction, sample_whale_address, sample_exchange_address):
        """Test generation of exchange deposit signal"""
        # Whale sending to exchange
        sample_transaction['from'] = sample_whale_address
        sample_transaction['to'] = sample_exchange_address
        sample_transaction['is_significant'] = True
        sample_transaction['value_eth'] = 500.0
        sample_transaction['transaction_type'] = 'send'
        sample_transaction['counterparty_category'] = 'exchange'

        signals = self.signal_generator.generate_signals(sample_transaction)

        assert len(signals) > 0
        # Exchange deposits are typically distribution signals with higher significance
        assert any(s.signal_type in [SignalType.DISTRIBUTION, SignalType.EXCHANGE_DEPOSIT]
                  for s in signals)

    def test_no_signals_for_insignificant_transaction(self, sample_transaction):
        """Test that insignificant transactions don't generate signals"""
        sample_transaction['is_significant'] = False
        sample_transaction['value_eth'] = 0.1

        signals = self.signal_generator.generate_signals(sample_transaction)

        # Should generate no signals or low strength signals
        assert len(signals) == 0 or all(s.strength == SignalStrength.LOW for s in signals)

    def test_signal_strength_calculation(self, sample_transaction, sample_whale_address):
        """Test that signal strength is calculated correctly based on value"""
        # Large transaction should generate high strength signal
        sample_transaction['to'] = sample_whale_address
        sample_transaction['is_significant'] = True
        sample_transaction['value_eth'] = 1000.0
        sample_transaction['transaction_type'] = 'receive'

        signals = self.signal_generator.generate_signals(sample_transaction)

        assert len(signals) > 0
        # At least one signal should have high or very high strength
        assert any(s.strength in [SignalStrength.HIGH, SignalStrength.VERY_HIGH]
                  for s in signals)
