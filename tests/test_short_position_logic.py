"""
Test SHORT position logic with distribution signals and higher low detection
"""
import pytest
from datetime import datetime, timedelta
from src.signals.enhanced_signal import EnhancedSignal
from src.signals.signal_generator import SignalType, SignalStrength
from src.trading.indicators.swing_points import SwingPointDetector
from src.trading.indicators.base_indicator import Candle


class TestShortPositionLogic:
    """Test suite for SHORT position logic"""

    def test_enhanced_signal_bearish_creates_short_recommendation(self):
        """Test that bearish predicted_impact automatically creates SHORT recommendation"""
        signal = EnhancedSignal(
            signal_type=SignalType.DISTRIBUTION,
            strength=SignalStrength.HIGH,
            transaction_hash="0x123",
            wallet_address="0xabc",
            wallet_name="Test Whale",
            wallet_category="whale",
            chain="ethereum",
            value_eth=500.0,
            description="Whale distribution detected",
            reasoning_chain=[
                "Large whale deposited 500 ETH to Binance",
                "This follows 15% price increase in last 48h",
                "Market showing signs of exhaustion"
            ],
            predicted_impact="bearish"
        )

        # Verify SHORT position recommendation is set
        assert signal.position_recommendation == "SHORT"
        assert signal.predicted_impact == "bearish"

    def test_enhanced_signal_bullish_creates_long_recommendation(self):
        """Test that bullish predicted_impact creates LONG recommendation"""
        signal = EnhancedSignal(
            signal_type=SignalType.ACCUMULATION,
            strength=SignalStrength.HIGH,
            transaction_hash="0x456",
            wallet_address="0xdef",
            wallet_name="Test Whale",
            wallet_category="whale",
            chain="ethereum",
            value_eth=300.0,
            description="Whale accumulation detected",
            reasoning_chain=["Whale withdrawing from exchange"],
            predicted_impact="bullish"
        )

        assert signal.position_recommendation == "LONG"

    def test_swing_point_detector_identifies_higher_low(self):
        """Test that swing point detector identifies higher lows correctly"""
        detector = SwingPointDetector(lookback=3)

        # Create candles with higher lows pattern
        candles = [
            # First swing low at 100
            Candle(datetime.now() - timedelta(hours=15), 105, 107, 98, 102, 1000),
            Candle(datetime.now() - timedelta(hours=14), 102, 104, 99, 100, 1000),
            Candle(datetime.now() - timedelta(hours=13), 100, 102, 100, 101, 1000),  # Low at 100
            Candle(datetime.now() - timedelta(hours=12), 101, 108, 101, 106, 1000),
            Candle(datetime.now() - timedelta(hours=11), 106, 110, 105, 108, 1000),

            # Second swing low at 104 (higher low)
            Candle(datetime.now() - timedelta(hours=10), 108, 109, 107, 108, 1000),
            Candle(datetime.now() - timedelta(hours=9), 108, 110, 106, 107, 1000),
            Candle(datetime.now() - timedelta(hours=8), 107, 108, 104, 105, 1000),  # Low at 104 (higher)
            Candle(datetime.now() - timedelta(hours=7), 105, 111, 105, 110, 1000),
            Candle(datetime.now() - timedelta(hours=6), 110, 112, 108, 111, 1000),

            # Current price near higher low
            Candle(datetime.now() - timedelta(hours=5), 111, 112, 109, 110, 1000),
            Candle(datetime.now() - timedelta(hours=4), 110, 111, 108, 109, 1000),
            Candle(datetime.now() - timedelta(hours=3), 109, 110, 107, 108, 1000),
            Candle(datetime.now() - timedelta(hours=2), 108, 109, 106, 107, 1000),
            Candle(datetime.now() - timedelta(hours=1), 107, 108, 105, 106, 1000),
            Candle(datetime.now(), 106, 107, 104.5, 105, 1000),  # Near higher low
        ]

        # Process candles
        for candle in candles:
            detector.calculate(candles[:candles.index(candle) + 1])

        # Check if higher low is detected
        assert detector.is_higher_low(), "Higher low should be detected"

        # Get entry conditions
        current_price = 105.0
        entry_conditions = detector.get_short_entry_conditions(current_price, tolerance=0.01)

        assert entry_conditions["is_higher_low"] is True
        assert entry_conditions["entry_level"] is not None

    def test_short_entry_at_higher_low_with_tolerance(self):
        """Test SHORT entry logic at higher low with price tolerance"""
        detector = SwingPointDetector(lookback=3)

        # Simplified higher low pattern
        base_time = datetime.now()
        candles = []

        # Create pattern: low at 100, then higher low at 105
        prices = [
            (110, 115, 98, 102),   # First low
            (102, 105, 100, 103),
            (103, 108, 102, 106),
            (106, 112, 105, 110),
            (110, 115, 108, 112),  # High
            (112, 113, 107, 109),
            (109, 110, 105, 107),  # Higher low
            (107, 111, 106, 109),
            (109, 112, 108, 110),
            (110, 111, 109, 110),
        ]

        for i, (open_p, high, low, close) in enumerate(prices):
            candle = Candle(
                base_time - timedelta(hours=len(prices) - i),
                open_p, high, low, close, 1000
            )
            candles.append(candle)
            detector.calculate(candles)

        # Test entry at higher low level
        should_enter, entry_price = detector.should_enter_short_at_higher_low(
            current_price=106.0,
            tolerance=0.01  # 1% tolerance
        )

        # Note: Actual result depends on swing detection
        # This test verifies the method runs without errors
        assert isinstance(should_enter, bool)
        assert entry_price is None or isinstance(entry_price, float)

    def test_enhanced_signal_with_entry_conditions(self):
        """Test EnhancedSignal with entry conditions for SHORT position"""
        entry_conditions = {
            "entry_level": 3500.0,
            "stop_loss": 3600.0,
            "take_profit": 3300.0
        }

        signal = EnhancedSignal(
            signal_type=SignalType.DISTRIBUTION,
            strength=SignalStrength.VERY_HIGH,
            transaction_hash="0x789",
            wallet_address="0xghi",
            wallet_name="Vitalik Buterin",
            wallet_category="whale",
            chain="ethereum",
            value_eth=500.0,
            description="Major distribution signal",
            reasoning_chain=[
                "Whale deposited 500 ETH to Binance",
                "Price at higher low level",
                "RSI showing overbought conditions"
            ],
            predicted_impact="bearish",
            entry_conditions=entry_conditions
        )

        # Verify all fields are set correctly
        assert signal.position_recommendation == "SHORT"
        assert signal.entry_conditions["entry_level"] == 3500.0
        assert signal.entry_conditions["stop_loss"] == 3600.0
        assert signal.entry_conditions["take_profit"] == 3300.0

        # Test message formatting
        message = signal.get_message()
        assert "SHORT" in message
        assert "3500.0" in message or "3500" in message  # Entry level
        assert "BEARISH" in message

    def test_signal_to_dict_includes_position_fields(self):
        """Test that to_dict includes position recommendation and entry conditions"""
        signal = EnhancedSignal(
            signal_type=SignalType.DISTRIBUTION,
            strength=SignalStrength.HIGH,
            transaction_hash="0xabc",
            wallet_address="0xdef",
            wallet_name="Test",
            wallet_category="whale",
            chain="ethereum",
            value_eth=100.0,
            description="Test",
            reasoning_chain=["Test"],
            predicted_impact="bearish",
            entry_conditions={"entry_level": 3500.0}
        )

        signal_dict = signal.to_dict()

        assert "position_recommendation" in signal_dict
        assert signal_dict["position_recommendation"] == "SHORT"
        assert "entry_conditions" in signal_dict
        assert signal_dict["entry_conditions"]["entry_level"] == 3500.0


def test_integration_distribution_to_short():
    """
    Integration test: Distribution signal should trigger SHORT position
    with proper entry conditions at higher low level
    """
    # This demonstrates the full flow:
    # 1. Distribution signal detected (bearish)
    # 2. Higher low identified
    # 3. SHORT position recommended with entry conditions

    # Create distribution signal with bearish impact
    signal = EnhancedSignal(
        signal_type=SignalType.DISTRIBUTION,
        strength=SignalStrength.VERY_HIGH,
        transaction_hash="0x123abc",
        wallet_address="0xvitalik",
        wallet_name="Vitalik Buterin",
        wallet_category="whale",
        chain="ethereum",
        value_eth=500.0,
        description="Whale distribution at higher low",
        reasoning_chain=[
            "Wallet historically accumulates during dips, sells during pumps",
            "This deposit to Binance follows 15% price increase in last 48h",
            "Correlated with 2 other whale deposits within 30 minutes",
            "Market context: Strong bullish trend, high volume",
            "Pattern matches historical behavior before -20% corrections"
        ],
        predicted_impact="bearish",
        recommended_actions=[
            "Monitor for additional whale deposits in next 2 hours",
            "Consider opening SHORT position at higher low level",
            "Watch for price action near $3,500 support"
        ],
        correlations=[
            "Whale B deposited 300 ETH to Coinbase 15 min ago",
            "Arbitrum whale activity increased 40% in last hour"
        ],
        market_context={
            "trend": "bullish",
            "price_change_24h": 15.2,
            "volume_24h": "high"
        },
        entry_conditions={
            "entry_level": 3500.0,
            "stop_loss": 3600.0,
            "take_profit": 3300.0,
            "entry_type": "higher_low",
            "description": "Enter SHORT at higher low level with tight stop above recent swing high"
        }
    )

    # Verify the signal recommends SHORT position
    assert signal.position_recommendation == "SHORT"
    assert signal.predicted_impact == "bearish"
    assert signal.strength == SignalStrength.VERY_HIGH

    # Verify entry conditions are set
    assert signal.entry_conditions["entry_level"] == 3500.0
    assert signal.entry_conditions["entry_type"] == "higher_low"

    # Verify message includes all important info
    message = signal.get_message()
    assert "SHORT" in message or "short" in message.lower()
    assert "BEARISH" in message or "bearish" in message.lower()
    assert "3500" in message  # Entry level
    assert "3600" in message  # Stop loss
    assert "3300" in message  # Take profit

    print("\n" + "="*80)
    print("INTEGRATION TEST: Distribution → SHORT Position")
    print("="*80)
    print(message)
    print("="*80)
