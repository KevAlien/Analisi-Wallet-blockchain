"""
Integration tests for the complete signal generation pipeline
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.analysis.transaction_analyzer import TransactionAnalyzer
from src.signals.signal_generator import SignalGenerator, SignalType, SignalStrength


class TestSignalPipeline:
    """Test the complete pipeline from transaction to signal"""

    def setup_method(self):
        """Setup test fixtures"""
        self.analyzer = TransactionAnalyzer()
        self.signal_generator = SignalGenerator()

    def test_complete_pipeline_accumulation(self, analyzed_accumulation_transaction):
        """Test complete pipeline for whale accumulation"""
        # Transaction is already analyzed, now generate signals
        signals = self.signal_generator.generate_signals(analyzed_accumulation_transaction)

        # Should have generated at least one signal
        assert len(signals) > 0

        # Verify signal properties
        for signal in signals:
            assert signal.transaction_hash is not None
            assert signal.chain is not None
            assert signal.timestamp is not None

        # Should be accumulation signal
        assert any(s.signal_type == SignalType.ACCUMULATION for s in signals)

    def test_complete_pipeline_distribution(self, analyzed_exchange_deposit_transaction):
        """Test complete pipeline for whale distribution to exchange"""
        # Transaction is already analyzed, now generate signals
        signals = self.signal_generator.generate_signals(analyzed_exchange_deposit_transaction)

        # Should have generated signals
        assert len(signals) > 0

        # Should be exchange deposit signal
        signal_types = [s.signal_type for s in signals]
        assert SignalType.EXCHANGE_DEPOSIT in signal_types

        # Verify high value signals have appropriate strength
        for signal in signals:
            if signal.value_eth >= 1000:
                assert signal.strength == SignalStrength.VERY_HIGH

    def test_pipeline_with_telegram_notification(
        self,
        analyzed_accumulation_transaction,
        mock_telegram_bot
    ):
        """Test pipeline including Telegram notification (mocked)"""
        # Generate signals from analyzed transaction
        signals = self.signal_generator.generate_signals(analyzed_accumulation_transaction)

        # Should have generated signals
        assert len(signals) > 0

        # Verify we can create notification message
        for signal in signals:
            message = signal.get_message()
            assert message is not None
            assert "Signal" in message or "SIGNAL" in message
            assert str(signal.value_eth) in message or f"{signal.value_eth:.2f}" in message
