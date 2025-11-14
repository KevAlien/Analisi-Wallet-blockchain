# Crypto Trading Bot

Automated cryptocurrency trading bot that combines on-chain whale tracking with advanced technical analysis strategies for profitable trading decisions.

## Features

### Trading Strategies

The bot implements 5 battle-tested crypto trading strategies:

1. **EMA Crossover with Heikin Ashi**
   - Fast/Slow EMA crossovers
   - Heikin Ashi confirmation for trend strength
   - Optimal for trend following on higher timeframes (1h, 4h)

2. **RSI Divergence Day Trading**
   - Detects bullish/bearish divergences
   - VWAP breakout confirmation
   - Perfect for day trading (5m, 15m timeframes)

3. **Scalping Triple Indicator** ⭐ (Best for scalping)
   - Combines Pivot Points, Stochastic RSI, and VWAP
   - All 3 indicators must confirm before entry
   - Optimal timeframe: 5-30 minutes

4. **Open Interest Analysis**
   - Analyzes futures market sentiment
   - Detects LONG/SHORT buildups
   - Requires Open Interest data from exchange APIs

5. **Divergence Detector**
   - Generic divergence detection across multiple oscillators
   - Works with RSI, MACD, Stochastic
   - EMA 200 trend filter

### Risk Management

- **Position Sizing**: Kelly Criterion, Fixed Fractional, Volatility-based
- **Stop Loss Management**: ATR-based dynamic stops
- **Portfolio Tracking**: Real-time PnL, win rate, profit factor
- **Risk Limits**: Maximum positions, maximum risk per trade

### Signal Aggregation

- Combines on-chain whale tracking with technical analysis
- AI-powered decision making (optional)
- Weighted scoring system
- Confidence-based execution

## Installation

```bash
# Clone the repository
git clone https://github.com/KevAlien/Analisi-Wallet-blockchain.git
cd Analisi-Wallet-blockchain

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your configuration
```

## Configuration

Edit `.env` file:

```bash
# Trading Configuration
TRADING_SYMBOLS=BTCUSDT,ETHUSDT
TRADING_TIMEFRAME=15m
CHECK_INTERVAL_SECONDS=60

# Enabled Strategies
ENABLED_STRATEGIES=EMA_CROSSOVER,RSI_DIVERGENCE,SCALPING_TRIPLE,DIVERGENCE_DETECTOR

# Risk Management
INITIAL_CAPITAL=10000
RISK_PER_TRADE_PCT=1.0
MAX_OPEN_POSITIONS=3
MAX_RISK_PCT=20.0

# Data Source
PRICE_SOURCE=BINANCE

# Notifications
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

## Usage

### Run the Trading Bot

```bash
# Standard mode
python trading_bot_main.py

# Dry run mode (no actual trades, analysis only)
python trading_bot_main.py --dry-run

# With custom config
python trading_bot_main.py --config prod.env

# Debug mode
python trading_bot_main.py --log-level DEBUG
```

### Run Whale Tracker Only

```bash
python main.py
```

### Combined Mode (Recommended)

The bot automatically integrates whale tracking signals when both systems are running. This provides the most profitable signals by combining:
- On-chain whale activity
- Technical analysis confirmations
- AI reasoning (optional)

## Architecture

```
src/
├── trading/
│   ├── indicators/         # Technical indicators (EMA, RSI, VWAP, etc.)
│   ├── strategies/         # Trading strategies
│   ├── risk/              # Risk management
│   └── execution/         # Order execution (TODO)
├── market_data/           # Price oracle (Binance, CoinGecko)
├── orchestration/         # Signal aggregator & trading bot
├── signals/               # On-chain signal generation (existing)
└── reasoning/             # AI reasoning engine (existing)
```

## Strategy Details

### EMA Crossover

**Entry (LONG)**:
- EMA 20 crosses above EMA 50
- Price closes above crossover
- Heikin Ashi turns green
- Next HA green candle exceeds previous

**Exit**:
- Opposite crossover
- Price breaks below EMA 200

**Parameters**: `EMA(20, 50, 200)` for higher timeframes, `EMA(8, 14, 50)` for day trading

---

### RSI Divergence

**Entry (LONG)**:
- RSI forms Higher Low
- Price forms Lower Low (bullish divergence)
- VWAP broken to upside
- Volume decreasing during retracement

**Exit**:
- Opposite divergence
- VWAP break to downside

**Timeframe**: 5-15 minutes optimal

---

### Scalping Triple Indicator

**Entry (LONG)** - ALL must occur:
1. Stochastic RSI: K crosses D from below
2. VWAP: Price breaks above
3. Pivot Points: Support established OR resistance broken
4. Confirmation: Next candle above current

**Exit**:
- Opposite Stochastic RSI crossover
- Price crosses below VWAP

**Timeframe**: 5-30 minutes (best 15m)

---

### Risk/Reward Ratios

| Strategy | Min R:R | Win Rate Target | Optimal Timeframe |
|----------|---------|-----------------|-------------------|
| EMA Crossover | 2:1 | 50%+ | 1h, 4h |
| RSI Divergence | 2.5:1 | 45%+ | 5m, 15m |
| Scalping Triple | 2:1 | 55%+ | 15m, 30m |
| Divergence Detector | 3:1 | 40%+ | 1h, 4h |

## Risk Management

### Position Sizing

```python
# Fixed Fractional (default)
# Risk 1% of capital per trade
position_size = (capital * risk_pct) / stop_distance

# Kelly Criterion (advanced)
# Optimal sizing based on win rate
kelly_pct = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
```

### Stop Loss Placement

- **ATR-based**: `stop_loss = entry - (2 × ATR)`
- **Swing-based**: Below recent swing low (LONG) or above swing high (SHORT)
- **Volatility-adjusted**: Larger stops for volatile assets

## Backtesting (Coming Soon)

```bash
python -m src.trading.backtesting.backtest_engine \
  --strategy SCALPING_TRIPLE \
  --symbol BTCUSDT \
  --timeframe 15m \
  --start 2024-01-01 \
  --end 2024-12-01
```

## Telegram Notifications

The bot sends real-time notifications for:
- Position opened (LONG/SHORT)
- Position closed (with PnL)
- Stop loss hit
- Take profit hit
- Daily performance summary

Example notification:
```
🟢 LONG Position Opened

Symbol: BTCUSDT
Entry: $45,230.50
Size: 0.0221 BTC
Stop Loss: $44,850.00
Take Profit: $46,000.00
Confidence: 87.5%

Strategy: Scalping Triple Indicator
```

## Performance Metrics

The bot tracks:
- Total trades
- Win rate
- Average win/loss
- Profit factor
- Maximum drawdown
- Sharpe ratio (coming soon)

## Safety & Best Practices

⚠️ **IMPORTANT**:
- Always start with **dry-run mode** to test strategies
- Never risk more than **1-2% per trade**
- Keep **maximum 3-5 open positions**
- Use **stop losses on every trade**
- Test strategies on different timeframes
- Monitor bot performance daily

## Troubleshooting

### Bot not generating signals
- Check if strategies are enabled in `.env`
- Verify API keys are correct
- Ensure sufficient candle data (200+ candles needed)
- Check logs: `tail -f trading_bot.log`

### High false signals
- Increase `RISK_PER_TRADE_PCT` threshold
- Enable fewer strategies simultaneously
- Use higher timeframes (less noise)
- Increase signal confidence threshold

### Positions not closing
- Verify stop loss/take profit are set
- Check price data source is active
- Review logs for errors

## Contributing

Contributions welcome! Areas for improvement:
- DEX integration (Uniswap, Sushiswap)
- Additional strategies (Ichimoku, Bollinger Bands)
- Machine learning signal enhancement
- Backtesting framework
- Live dashboard

## License

MIT License - See LICENSE file

## Disclaimer

⚠️ **Trading cryptocurrencies involves substantial risk of loss. This bot is for educational and research purposes only. Never invest more than you can afford to lose. Past performance does not guarantee future results. Use at your own risk.**

## Support

- Issues: https://github.com/KevAlien/Analisi-Wallet-blockchain/issues
- Telegram: [Your support channel]
- Documentation: See `Memory-Bank/` directory

---

Made with ❤️ by KevAlien | Powered by AI Reasoning
