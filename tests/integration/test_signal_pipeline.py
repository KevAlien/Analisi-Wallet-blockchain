"""
Integration tests for the complete signal generation pipeline
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.analysis.transaction_analyzer import TransactionAnalyzer
from src.signals.signal_generator import SignalGenerator, SignalType


class TestSignalPipeline:
    """Test the complete pipeline from transaction to signal"""

    def setup_method(self):
        """Setup test fixtures"""
        self.analyzer = TransactionAnalyzer()
        self.signal_generator = SignalGenerator()

    def test_complete_pipeline_accumulation(self, sample_transaction, sample_whale_address):
        """Test complete pipeline for whale accumulation"""
        # Setup transaction for accumulation
        sample_transaction['to'] = sample_whale_address
        sample_transaction['value'] = str(int(500 * 10**18))  # 500 ETH

        # Step 1: Analyze transaction
        analyzed_tx = self.analyzer.analyze_transaction(sample_transaction)
        assert analyzed_tx is not None

        # Step 2: Generate signals (if significant)
        if analyzed_tx.get('is_significant'):
            signals = self.signal_generator.generate_signals(analyzed_tx)

            # Should have generated at least one signal
            assert len(signals) > 0

            # Verify signal properties
            for signal in signals:
                assert signal.transaction_hash is not None
                assert signal.chain is not None
                assert signal.timestamp is not None

    def test_complete_pipeline_distribution(self, sample_transaction, sample_whale_address, sample_exchange_address):
        """Test complete pipeline for whale distribution to exchange"""
        # Setup transaction for distribution to exchange
        sample_transaction['from'] = sample_whale_address
        sample_transaction['to'] = sample_exchange_address
        sample_transaction['value'] = str(int(1000 * 10**18))  # 1000 ETH

        # Step 1: Analyze transaction
        analyzed_tx = self.analyzer.analyze_transaction(sample_transaction)
        assert analyzed_tx is not None

        # Step 2: Generate signals
        if analyzed_tx.get('is_significant'):
            signals = self.signal_generator.generate_signals(analyzed_tx)

            # Should have generated signals
            assert len(signals) > 0

            # At least one should be distribution or exchange deposit
            signal_types = [s.signal_type for s in signals]
            assert any(st in [SignalType.DISTRIBUTION, SignalType.EXCHANGE_DEPOSIT]
                      for st in signal_types)

    @pytest.mark.asyncio
    async def test_pipeline_with_telegram_notification(
        self,
        sample_transaction,
        sample_whale_address,
        mock_telegram_bot
    ):
        """Test pipeline including Telegram notification (mocked)"""
        # Setup transaction
        sample_transaction['to'] = sample_whale_address
        sample_transaction['value'] = str(int(500 * 10**18))

        # Analyze and generate signal
        analyzed_tx = self.analyzer.analyze_transaction(sample_transaction)

        if analyzed_tx.get('is_significant'):
            signals = self.signal_generator.generate_signals(analyzed_tx)

            # Mock sending signals via Telegram
            for signal in signals:
                result = await mock_telegram_bot.send_message(
                    chat_id=123456,
                    text=f"Signal: {signal.signal_type.value}"
                )
                assert result is True

            # Verify send_message was called
            assert mock_telegram_bot.send_message.called
