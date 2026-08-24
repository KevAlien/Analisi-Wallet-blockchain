"""
Tests for signal generation functionality

This test module validates that the SignalGenerator correctly creates
trading signals from analyzed blockchain transactions. Tests cover:
- Signal type detection (accumulation, distribution, exchange)
- Signal strength calculation based on transaction value
- Proper handling of insignificant transactions
- Wallet info extraction and validation
"""
import pytest
from datetime import datetime
from src.signals.signal_generator import SignalGenerator, SignalType, SignalStrength
from tests.conftest import assert_signal_valid, create_test_transaction


class TestSignalGenerator:
    """Test cases for SignalGenerator"""

    def setup_method(self):
        """Setup test fixtures - runs before each test method"""
        self.signal_generator = SignalGenerator()

    def test_signal_generator_initialization(self):
        """Test that SignalGenerator initializes correctly"""
        assert self.signal_generator is not None
        assert hasattr(self.signal_generator, 'generate_signals')
        assert callable(self.signal_generator.generate_signals)

    def test_generate_accumulation_signal(self, analyzed_accumulation_transaction):
        """Test generation of accumulation signal for whale receiving funds"""
        # Act
        signals = self.signal_generator.generate_signals(analyzed_accumulation_transaction)

        # Assert - should generate at least one signal
        assert len(signals) > 0, "No signals generated for accumulation"

        # Check signal type
        accumulation_signals = [s for s in signals if s.signal_type == SignalType.ACCUMULATION]
        assert len(accumulation_signals) > 0, "No accumulation signal found"

        # Validate signal using helper
        signal = accumulation_signals[0]
        assert_signal_valid(signal, SignalType.ACCUMULATION, min_value=500.0)

        # Verify specific properties
        assert signal.wallet_name == "Test Whale"
        assert signal.wallet_category == "whale"
        assert signal.value_eth == 500.0
        assert "whale" in signal.tags

    def test_generate_distribution_signal(self, analyzed_distribution_transaction):
        """Test generation of distribution signal for whale sending funds"""
        # Act
        signals = self.signal_generator.generate_signals(analyzed_distribution_transaction)

        # Assert
        assert len(signals) > 0, "No signals generated for distribution"

        # Check signal type
        distribution_signals = [s for s in signals if s.signal_type == SignalType.DISTRIBUTION]
        assert len(distribution_signals) > 0, "No distribution signal found"

        # Validate signal
        signal = distribution_signals[0]
        assert_signal_valid(signal, SignalType.DISTRIBUTION, min_value=500.0)

        # Verify whale wallet info is preserved
        assert signal.wallet_name == "Test Whale"
        assert signal.wallet_category == "whale"
        assert signal.value_eth == 500.0

    def test_exchange_deposit_signal(self, analyzed_exchange_deposit_transaction):
        """Test generation of exchange deposit signal (potential sell indicator)"""
        # Act
        signals = self.signal_generator.generate_signals(analyzed_exchange_deposit_transaction)

        # Assert
        assert len(signals) > 0, "No signals generated for exchange deposit"

        # Exchange deposits should generate EXCHANGE_DEPOSIT signals
        exchange_signals = [s for s in signals if s.signal_type == SignalType.EXCHANGE_DEPOSIT]
        assert len(exchange_signals) > 0, "No exchange deposit signal found"

        # Validate signal
        signal = exchange_signals[0]
        assert_signal_valid(signal, SignalType.EXCHANGE_DEPOSIT, min_value=1000.0)

        # Verify exchange tag is added
        assert signal.wallet_name == "Test Whale"
        assert signal.value_eth == 1000.0
        assert "exchange" in signal.tags, "Exchange tag not added to signal"

    def test_no_signals_for_insignificant_transaction(self, sample_transaction):
        """Test that insignificant transactions don't generate signals"""
        sample_transaction['is_significant'] = False
        sample_transaction['value_eth'] = 0.1

        signals = self.signal_generator.generate_signals(sample_transaction)

        # Should generate no signals or low strength signals
        assert len(signals) == 0 or all(s.strength == SignalStrength.LOW for s in signals)

    def test_signal_strength_calculation(self, analyzed_exchange_deposit_transaction):
        """Test that signal strength is calculated correctly based on value"""
        # 1000 ETH transaction should generate VERY_HIGH strength signal
        # Strength thresholds: 1000+ = VERY_HIGH, 500-999 = HIGH, 200-499 = MEDIUM, <200 = LOW

        # Act
        signals = self.signal_generator.generate_signals(analyzed_exchange_deposit_transaction)

        # Assert
        assert len(signals) > 0, "No signals generated"
        signal = signals[0]

        # Validate strength for 1000+ ETH
        assert signal.strength == SignalStrength.VERY_HIGH, \
            f"Expected VERY_HIGH strength for 1000 ETH, got {signal.strength}"
        assert signal.value_eth >= 1000.0

    def test_signal_strength_thresholds(self):
        """Test various signal strength thresholds"""
        test_cases = [
            (1500.0, SignalStrength.VERY_HIGH),  # >= 1000
            (750.0, SignalStrength.HIGH),        # >= 500
            (300.0, SignalStrength.MEDIUM),      # >= 200
            (150.0, SignalStrength.LOW),         # < 200
        ]

        for value_eth, expected_strength in test_cases:
            # Create transaction with specific value
            tx = create_test_transaction(value_eth=value_eth, direction="incoming")

            # Generate signals
            signals = self.signal_generator.generate_signals(tx)

            # Verify strength
            assert len(signals) > 0, f"No signals for {value_eth} ETH"
            assert signals[0].strength == expected_strength, \
                f"Expected {expected_strength} for {value_eth} ETH, got {signals[0].strength}"
