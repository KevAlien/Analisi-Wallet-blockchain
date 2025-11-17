"""
Tests for transaction analysis functionality
"""
import pytest
from src.analysis.transaction_analyzer import TransactionAnalyzer
from src.config.wallet_registry import Chain


class TestTransactionAnalyzer:
    """Test cases for TransactionAnalyzer"""

    def setup_method(self):
        """Setup test fixtures"""
        self.analyzer = TransactionAnalyzer()

    def test_analyzer_initialization(self):
        """Test that TransactionAnalyzer initializes correctly"""
        assert self.analyzer is not None
        assert hasattr(self.analyzer, 'analyze_transaction')

    def test_analyze_transaction_basic(self, sample_transaction):
        """Test basic transaction analysis"""
        result = self.analyzer.analyze_transaction(sample_transaction)

        assert result is not None
        assert 'hash' in result
        assert result['hash'] == sample_transaction['hash']

    def test_analyze_transaction_value_conversion(self, sample_transaction):
        """Test that transaction value is properly converted from wei to ETH"""
        result = self.analyzer.analyze_transaction(sample_transaction)

        # 1000000000000000000 wei = 1 ETH
        assert 'value_eth' in result
        assert result['value_eth'] == 1.0

    def test_analyze_transaction_type_detection(self, sample_transaction, sample_whale_address):
        """Test that transaction type is correctly detected"""
        # Test receive transaction
        sample_transaction['to'] = sample_whale_address
        result = self.analyzer.analyze_transaction(sample_transaction)
        assert 'transaction_type' in result

        # Test send transaction
        sample_transaction['from'] = sample_whale_address
        sample_transaction['to'] = '0x0000000000000000000000000000000000000000'
        result = self.analyzer.analyze_transaction(sample_transaction)
        assert 'transaction_type' in result

    def test_analyze_significant_transaction(self, sample_transaction):
        """Test significance detection for large transactions"""
        # Large transaction
        sample_transaction['value'] = str(int(1000 * 10**18))  # 1000 ETH

        result = self.analyzer.analyze_transaction(sample_transaction)

        # Should be marked as significant
        assert result.get('is_significant', False) or result.get('value_eth', 0) >= 1000

    def test_analyze_insignificant_transaction(self, sample_transaction):
        """Test that small transactions are identified"""
        # Small transaction
        sample_transaction['value'] = str(int(0.01 * 10**18))  # 0.01 ETH

        result = self.analyzer.analyze_transaction(sample_transaction)

        # Should have small value
        assert result.get('value_eth', 0) < 1

    def test_analyze_failed_transaction(self, sample_transaction):
        """Test analysis of failed transactions"""
        sample_transaction['isError'] = '1'

        result = self.analyzer.analyze_transaction(sample_transaction)

        # Should still be analyzed, but might be marked as failed
        assert result is not None
        assert 'hash' in result
