"""
Trading Bot Orchestrator - Main coordinator for automated crypto trading.

Integrates:
- On-chain whale tracking (existing system)
- Technical analysis strategies
- Risk management
- Signal aggregation
- Trade execution
"""
import asyncio
import logging
from typing import List, Optional, Dict
from datetime import datetime

from ..market_data import PriceOracle, PriceSource
from ..trading.strategies import (
    EMACrossoverStrategy,
    RSIDivergenceStrategy,
    ScalpingTripleStrategy,
    DivergenceDetectorStrategy,
    BaseStrategy,
    TradingSignal,
    SignalType
)
from ..trading.risk import PositionSizer, PortfolioTracker, Position, PositionStatus
from .signal_aggregator import SignalAggregator, AggregatedSignalType
from ..notifications.telegram_bot import TelegramNotifier

logger = logging.getLogger(__name__)


class TradingBot:
    """Main trading bot orchestrator."""

    def __init__(self, config: Dict):
        """
        Initialize Trading Bot.

        Args:
            config: Configuration dictionary
        """
        self.config = config

        # Initialize components
        self.price_oracle = PriceOracle(
            primary_source=PriceSource[config.get('PRICE_SOURCE', 'BINANCE')]
        )

        # Initialize strategies based on config
        self.strategies: List[BaseStrategy] = []
        self._initialize_strategies(config)

        # Risk management
        initial_capital = float(config.get('INITIAL_CAPITAL', 10000))
        self.position_sizer = PositionSizer(
            risk_per_trade_pct=float(config.get('RISK_PER_TRADE_PCT', 1.0))
        )
        self.portfolio = PortfolioTracker(initial_capital)

        # Signal aggregation
        self.signal_aggregator = SignalAggregator(use_ai_reasoning=False)  # Set to True if AI enabled

        # Notifications
        self.notifier = None
        if config.get('TELEGRAM_BOT_TOKEN') and config.get('TELEGRAM_CHAT_ID'):
            self.notifier = TelegramNotifier(
                config['TELEGRAM_BOT_TOKEN'],
                config['TELEGRAM_CHAT_ID']
            )

        # State
        self.running = False
        self.symbols = config.get('TRADING_SYMBOLS', ['BTCUSDT', 'ETHUSDT'])
        self.check_interval = int(config.get('CHECK_INTERVAL_SECONDS', 60))

    def _initialize_strategies(self, config: Dict):
        """Initialize trading strategies based on configuration."""
        enabled_strategies = config.get('ENABLED_STRATEGIES', [
            'EMA_CROSSOVER',
            'RSI_DIVERGENCE',
            'SCALPING_TRIPLE',
            'DIVERGENCE_DETECTOR'
        ])

        timeframe = config.get('TIMEFRAME', '15m')

        if 'EMA_CROSSOVER' in enabled_strategies:
            self.strategies.append(EMACrossoverStrategy(
                fast_period=20,
                slow_period=50,
                trend_period=200,
                timeframe=timeframe
            ))

        if 'RSI_DIVERGENCE' in enabled_strategies:
            self.strategies.append(RSIDivergenceStrategy(
                rsi_period=14,
                timeframe=timeframe
            ))

        if 'SCALPING_TRIPLE' in enabled_strategies:
            self.strategies.append(ScalpingTripleStrategy(timeframe=timeframe))

        if 'DIVERGENCE_DETECTOR' in enabled_strategies:
            self.strategies.append(DivergenceDetectorStrategy(timeframe=timeframe))

        logger.info(f"Initialized {len(self.strategies)} trading strategies")

    async def start(self):
        """Start the trading bot."""
        self.running = True
        logger.info("Trading bot started")

        if self.notifier:
            await self.notifier.send_message("🤖 Trading Bot Started\n\nMonitoring markets...")

        try:
            while self.running:
                await self._trading_loop()
                await asyncio.sleep(self.check_interval)

        except KeyboardInterrupt:
            logger.info("Trading bot stopped by user")
        except Exception as e:
            logger.error(f"Trading bot error: {e}", exc_info=True)
        finally:
            await self.stop()

    async def stop(self):
        """Stop the trading bot."""
        self.running = False
        logger.info("Trading bot stopped")

        if self.notifier:
            metrics = self.portfolio.get_performance_metrics()
            await self.notifier.send_message(
                f"🛑 Trading Bot Stopped\n\n"
                f"Total Trades: {metrics['total_trades']}\n"
                f"Win Rate: {metrics['win_rate']*100:.1f}%\n"
                f"Total PnL: ${metrics['total_pnl']:.2f}\n"
                f"Return: {metrics['total_return_pct']:.2f}%"
            )

    async def _trading_loop(self):
        """Main trading loop - executed every interval."""
        try:
            for symbol in self.symbols:
                await self._process_symbol(symbol)

            # Check stop losses and take profits for open positions
            await self._check_position_exits()

        except Exception as e:
            logger.error(f"Error in trading loop: {e}", exc_info=True)

    async def _process_symbol(self, symbol: str):
        """Process trading signals for a symbol."""
        try:
            # Fetch current price and candles
            current_price = await self.price_oracle.get_current_price(symbol.replace('USDT', '').lower())
            if not current_price:
                logger.warning(f"Could not fetch price for {symbol}")
                return

            # Get historical candles for technical analysis
            candles = await self.price_oracle.get_historical_candles(
                symbol,
                interval=self.config.get('TIMEFRAME', '15m'),
                limit=200
            )

            if not candles:
                logger.warning(f"Could not fetch candles for {symbol}")
                return

            # Run all strategies
            ta_signals = []
            for strategy in self.strategies:
                try:
                    signal = strategy.analyze(candles)
                    if signal:
                        ta_signals.append(signal)
                        logger.info(f"{strategy.name} generated {signal.signal_type.value} signal for {symbol}")
                except Exception as e:
                    logger.error(f"Error in strategy {strategy.name}: {e}")

            # Aggregate signals (for now, just use TA signals; on-chain signals can be added later)
            if ta_signals:
                aggregated = self.signal_aggregator.aggregate_signals(
                    symbol=symbol,
                    current_price=current_price,
                    on_chain_signals=[],  # TODO: Integrate with whale tracking
                    ta_signals=ta_signals
                )

                if aggregated and self.signal_aggregator.is_actionable(aggregated):
                    await self._handle_aggregated_signal(aggregated, symbol, current_price)

        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}", exc_info=True)

    async def _handle_aggregated_signal(self, signal, symbol: str, current_price: float):
        """Handle an actionable aggregated signal."""
        # Check if we can open a new position
        can_trade, reason = self.portfolio.risk_check(
            max_open_positions=int(self.config.get('MAX_OPEN_POSITIONS', 3)),
            max_risk_pct=float(self.config.get('MAX_RISK_PCT', 20.0))
        )

        if not can_trade:
            logger.warning(f"Cannot open position for {symbol}: {reason}")
            return

        # Determine position side
        if signal.signal_type in [AggregatedSignalType.STRONG_BUY, AggregatedSignalType.BUY]:
            await self._open_long_position(signal, symbol, current_price)
        elif signal.signal_type in [AggregatedSignalType.STRONG_SELL, AggregatedSignalType.SELL]:
            await self._open_short_position(signal, symbol, current_price)

    async def _open_long_position(self, signal, symbol: str, current_price: float):
        """Open a LONG position."""
        # Calculate position size
        stop_loss = signal.recommended_stop_loss or current_price * 0.98  # 2% default
        position_size = self.position_sizer.calculate_position_size(
            capital=self.portfolio.current_capital,
            entry_price=current_price,
            stop_loss_price=stop_loss
        )

        # Validate position
        is_valid, validation_msg = self.position_sizer.validate_position(
            position_size, current_price, self.portfolio.current_capital
        )

        if not is_valid:
            logger.warning(f"Position validation failed for {symbol}: {validation_msg}")
            return

        # Create position
        position = Position(
            symbol=symbol,
            entry_price=current_price,
            size=position_size,
            side="LONG",
            entry_time=datetime.now(),
            stop_loss=stop_loss,
            take_profit=signal.recommended_take_profit,
            metadata={'signal_confidence': signal.confidence}
        )

        self.portfolio.add_position(position)

        logger.info(f"Opened LONG position on {symbol} at {current_price:.2f}, size: {position_size:.4f}")

        # Send notification
        if self.notifier:
            await self.notifier.send_message(
                f"🟢 LONG Position Opened\n\n"
                f"Symbol: {symbol}\n"
                f"Entry: ${current_price:.2f}\n"
                f"Size: {position_size:.4f}\n"
                f"Stop Loss: ${stop_loss:.2f}\n"
                f"Take Profit: ${signal.recommended_take_profit:.2f}\n"
                f"Confidence: {signal.confidence:.1f}%"
            )

    async def _open_short_position(self, signal, symbol: str, current_price: float):
        """Open a SHORT position (similar to LONG but opposite)."""
        stop_loss = signal.recommended_stop_loss or current_price * 1.02  # 2% default
        position_size = self.position_sizer.calculate_position_size(
            capital=self.portfolio.current_capital,
            entry_price=current_price,
            stop_loss_price=stop_loss
        )

        is_valid, validation_msg = self.position_sizer.validate_position(
            position_size, current_price, self.portfolio.current_capital
        )

        if not is_valid:
            logger.warning(f"Position validation failed for {symbol}: {validation_msg}")
            return

        position = Position(
            symbol=symbol,
            entry_price=current_price,
            size=position_size,
            side="SHORT",
            entry_time=datetime.now(),
            stop_loss=stop_loss,
            take_profit=signal.recommended_take_profit,
            metadata={'signal_confidence': signal.confidence}
        )

        self.portfolio.add_position(position)
        logger.info(f"Opened SHORT position on {symbol} at {current_price:.2f}")

        if self.notifier:
            await self.notifier.send_message(
                f"🔴 SHORT Position Opened\n\n"
                f"Symbol: {symbol}\n"
                f"Entry: ${current_price:.2f}\n"
                f"Size: {position_size:.4f}\n"
                f"Stop Loss: ${stop_loss:.2f}\n"
                f"Confidence: {signal.confidence:.1f}%"
            )

    async def _check_position_exits(self):
        """Check if any open positions should be exited."""
        for position in self.portfolio.get_open_positions():
            try:
                # Fetch current price
                current_price = await self.price_oracle.get_current_price(
                    position.symbol.replace('USDT', '').lower()
                )

                if not current_price:
                    continue

                # Check stop loss
                if self.portfolio.check_stop_loss(position, current_price):
                    await self._close_position(position, current_price, "Stop Loss Hit")

                # Check take profit
                elif self.portfolio.check_take_profit(position, current_price):
                    await self._close_position(position, current_price, "Take Profit Hit")

            except Exception as e:
                logger.error(f"Error checking exit for {position.symbol}: {e}")

    async def _close_position(self, position: Position, exit_price: float, reason: str):
        """Close a position."""
        self.portfolio.close_position(position.symbol, exit_price, datetime.now())

        logger.info(f"Closed {position.side} position on {position.symbol} at {exit_price:.2f}. Reason: {reason}")

        if self.notifier:
            pnl_emoji = "✅" if position.pnl > 0 else "❌"
            await self.notifier.send_message(
                f"{pnl_emoji} Position Closed\n\n"
                f"Symbol: {position.symbol}\n"
                f"Side: {position.side}\n"
                f"Entry: ${position.entry_price:.2f}\n"
                f"Exit: ${exit_price:.2f}\n"
                f"PnL: ${position.pnl:.2f} ({position.pnl_pct:.2f}%)\n"
                f"Reason: {reason}"
            )
