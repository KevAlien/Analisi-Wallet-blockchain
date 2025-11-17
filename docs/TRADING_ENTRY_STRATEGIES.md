# Trading Entry Strategies

This document describes the optimal entry point strategies implemented in the trading system.

## Overview

The system implements **10 high-probability entry strategies** (5 LONG, 5 SHORT) with an **A+ Setup Confluence Checker** that validates setups against 5 critical criteria to achieve 60-75% win rates.

---

## LONG ENTRY STRATEGIES

### 1. Bullish Divergence + Confirmations (`LongBullishDivergenceStrategy`)

**Best for:** Trend reversals from oversold conditions

**Entry Conditions:**
- Price makes Lower Low, RSI/Oscillator makes Higher Low (bullish divergence)
- Volume decreasing on retracement
- Entry: local resistance breakout with expansive volume (1.5x average)
- Stop: below swing low (max 3% from entry)

**Usage:**
```python
from src.trading.strategies import LongBullishDivergenceStrategy

strategy = LongBullishDivergenceStrategy(
    rsi_period=14,
    swing_lookback=20,
    volume_threshold=1.5,
    timeframe="15m"
)

signal = strategy.analyze(candles)
```

---

### 2. EMA Bounce + Structure (`LongEMABounceStrategy`)

**Best for:** Trend continuation trades in established uptrends

**Entry Conditions:**
- Price retests EMA 200 (4H) or EMA 50 (1H) as support
- Rejection candle (hammer, bullish engulfing)
- Price above faster EMAs (20/50)
- Entry: candle close above EMA + body greater than 50%

**Usage:**
```python
from src.trading.strategies import LongEMABounceStrategy

strategy = LongEMABounceStrategy(
    slow_ema_period=200,  # 200 for 4H, 50 for 1H
    medium_ema_period=50,
    fast_ema_period=20,
    min_body_ratio=0.5,
    timeframe="4h"
)

signal = strategy.analyze(candles)
```

---

### 3. Key Support + Long Buildup (OI) (`LongSupportOIBuildupStrategy`)

**Best for:** Breakout from accumulation zones

**Entry Conditions:**
- Level tested 2-3 times on higher timeframe
- Open Interest increasing + stable price/slight uptrend
- Volume profile: high volume at support
- Entry: intraday resistance breakout with OI confirmation

**Usage:**
```python
from src.trading.strategies import LongSupportOIBuildupStrategy

strategy = LongSupportOIBuildupStrategy(
    volume_profile_lookback=100,
    min_touches=2,
    oi_increase_threshold=1.1,
    timeframe="1h"
)

signal = strategy.analyze(candles, open_interest=oi_data)
```

---

### 4. Pivot Point + Triple Confluence (`LongPivotConfluenceStrategy`)

**Best for:** High probability reversal at pivot support

**Entry Conditions:**
- Price at S1 or S2 (standard pivot)
- Stochastic RSI bullish crossover (K above D, below 20)
- VWAP broken to the upside
- Entry: micro resistance breakout, next candle confirmation

**Usage:**
```python
from src.trading.strategies import LongPivotConfluenceStrategy

strategy = LongPivotConfluenceStrategy(
    stoch_rsi_period=14,
    vwap_reset_daily=True,
    oversold_threshold=20.0,
    timeframe="1h"
)

signal = strategy.analyze(candles)
```

---

### 5. Fibonacci + Accumulation (`LongFibonacciAccumulationStrategy`)

**Best for:** Golden zone (0.618-0.786) reversals

**Entry Conditions:**
- Retracement 0.618-0.786 from last impulse
- Consolidation 8-12 candles on operational timeframe
- Decreasing volume in consolidation
- Entry: range high breakout with 1.5x average volume

**Usage:**
```python
from src.trading.strategies import LongFibonacciAccumulationStrategy

strategy = LongFibonacciAccumulationStrategy(
    fib_lookback=50,
    min_consolidation_candles=8,
    max_consolidation_candles=12,
    volume_threshold=1.5,
    timeframe="15m"
)

signal = strategy.analyze(candles)
```

---

## SHORT ENTRY STRATEGIES

### 1. Bearish Divergence + Top Signals (`ShortBearishDivergenceStrategy`)

**Best for:** Top reversals from overbought conditions

**Entry Conditions:**
- Price makes Higher High, RSI makes Lower High (bearish divergence)
- Decreasing volume on pump
- Entry: support breakdown + EMA 200 as resistance
- Stop: above last high (max 3% from entry)

**Usage:**
```python
from src.trading.strategies import ShortBearishDivergenceStrategy

strategy = ShortBearishDivergenceStrategy(
    rsi_period=14,
    ema_period=200,
    swing_lookback=20,
    timeframe="15m"
)

signal = strategy.analyze(candles)
```

---

### 2. EMA Rejection + Bearish Structure (`ShortEMARejectionStrategy`)

**Best for:** Trend continuation shorts in established downtrends

**Entry Conditions:**
- Price rejected by EMA 200 (candles with long upper wicks)
- Price below EMA 20/50
- Death Cross (50 below 200) on higher timeframe
- Entry: local support break + failed retest

**Usage:**
```python
from src.trading.strategies import ShortEMARejectionStrategy

strategy = ShortEMARejectionStrategy(
    slow_ema_period=200,
    medium_ema_period=50,
    fast_ema_period=20,
    min_wick_ratio=0.6,
    timeframe="4h"
)

signal = strategy.analyze(candles)
```

---

### 3. Key Resistance + Short Buildup (OI) (`ShortResistanceOIBuildupStrategy`)

**Best for:** Breakdown from distribution zones

**Entry Conditions:**
- Multi-touch resistance level on higher timeframe
- OI increasing + price decreasing = short buildup
- Volume spike on rejection (1.5x average)
- Entry: intraday support break with decreasing OI confirmation

**Usage:**
```python
from src.trading.strategies import ShortResistanceOIBuildupStrategy

strategy = ShortResistanceOIBuildupStrategy(
    volume_profile_lookback=100,
    min_touches=2,
    oi_increase_threshold=1.1,
    volume_spike_threshold=1.5,
    timeframe="1h"
)

signal = strategy.analyze(candles, open_interest=oi_data)
```

---

### 4. Head & Shoulders Pattern (`ShortHeadShouldersStrategy`)

**Best for:** Major top reversals (EmperorBTC pattern)

**Entry Conditions:**
- Clearly defined neckline
- Volume: high on left shoulder, lower on head, minimum on right shoulder
- Entry: neckline break + failed retest
- Target: head-neckline distance projected downward

**Usage:**
```python
from src.trading.strategies import ShortHeadShouldersStrategy

strategy = ShortHeadShouldersStrategy(
    lookback=100,
    min_pattern_width=20,
    timeframe="4h"
)

signal = strategy.analyze(candles)
```

---

### 5. Overextension + Reversal Candles (`ShortOverextensionReversalStrategy`)

**Best for:** Extreme overextension reversals / Mean reversion

**Entry Conditions:**
- Price >3 standard deviations above moving average
- RSI >70 persistent (4H/Daily)
- Candle pattern: shooting star, bearish engulfing, dark cloud cover
- Entry: break of reversal candle low

**Usage:**
```python
from src.trading.strategies import ShortOverextensionReversalStrategy

strategy = ShortOverextensionReversalStrategy(
    ma_period=20,
    std_dev_threshold=3.0,
    rsi_period=14,
    rsi_overbought=70.0,
    timeframe="4h"
)

signal = strategy.analyze(candles)
```

---

## A+ SETUP CONFLUENCE CHECKER

The A+ Confluence Checker validates that a trading setup has **at least 4 out of 5 critical confluences**, which increases win rate to 60-75%.

### Critical Confluences (requires 4/5):

1. ✅ **Major structural level** (weekly/daily S/R)
2. ✅ **Confirmed RSI divergence**
3. ✅ **Specific candlestick pattern**
4. ✅ **Volume profile/OI alignment**
5. ✅ **EMA dynamical support/resistance**

### Usage:

```python
from src.trading.strategies import APlusConfluenceChecker, SignalType

checker = APlusConfluenceChecker(
    rsi_period=14,
    ema_periods=[20, 50, 200],
    volume_profile_lookback=100
)

# Check if LONG setup is A+
result = checker.check_confluence(
    candles=candles,
    signal_type=SignalType.LONG,
    current_price=current_price,
    open_interest=oi_data  # Optional
)

if result.is_aplus:
    print(f"✅ A+ Setup! Score: {result.score}/5")
    print(f"Met criteria: {result.met_criteria}")
    print(f"Missing: {result.missing_criteria}")
else:
    print(f"❌ Not A+ setup. Score: {result.score}/5")
```

---

## TIMING & INVALIDATION RULES

### Precise Timing:
- **Identification timeframe:** 4H-Daily for levels
- **Entry timeframe:** 15m-1H for execution
- **Confirmation:** Always wait for candle close

### Immediate Invalidation:
- **LONG:** Stop below swing low (2-3% max from entry)
- **SHORT:** Stop above swing high (2-3% max from entry)
- **Position reassessment:** If opposite move >50% of target distance

---

## NEW INDICATORS

The following technical indicators were added to support these strategies:

### `FibonacciRetracement`
Calculates Fibonacci retracement levels (0.236, 0.382, 0.5, 0.618, 0.786)

```python
from src.trading.indicators import FibonacciRetracement

fib = FibonacciRetracement(lookback=50)
fib.calculate(candles)

# Check if price in golden zone (0.618-0.786)
if fib.is_in_golden_zone(current_price):
    print("Price in golden zone!")
```

### `VolumeProfile`
Analyzes volume distribution across price levels

```python
from src.trading.indicators import VolumeProfile

vp = VolumeProfile(lookback=100, num_bins=50)
vp.calculate(candles)

# Get high volume nodes (support/resistance)
supports = vp.get_support_levels(current_price, count=3)
resistances = vp.get_resistance_levels(current_price, count=3)
```

### `CandlestickPatterns`
Detects common candlestick patterns

```python
from src.trading.indicators import CandlestickPatterns

patterns = CandlestickPatterns()
patterns.calculate(candles)

# Check for patterns
if patterns.has_bullish_pattern():
    print(f"Bullish patterns: {patterns.get_patterns()}")
```

### `StandardDeviation`
Measures price volatility and overextension (Bollinger Bands)

```python
from src.trading.indicators import StandardDeviation

std_dev = StandardDeviation(period=20, num_std=2.0)
std_dev.calculate(candles)

# Check overextension
if std_dev.is_overextended_above(current_price, num_std=3.0):
    print("Price overextended above mean!")
```

### `HeadAndShoulders`
Detects Head & Shoulders patterns (bearish and inverse)

```python
from src.trading.indicators import HeadAndShoulders

hs = HeadAndShoulders(lookback=100, min_pattern_width=20)
hs.calculate(candles)

if hs.has_pattern():
    pattern = hs.get_pattern()
    print(f"Pattern detected! Neckline: {pattern.neckline_price}")
```

---

## EXAMPLE: COMPLETE TRADING WORKFLOW

```python
from src.trading.strategies import (
    LongBullishDivergenceStrategy,
    ShortBearishDivergenceStrategy,
    APlusConfluenceChecker,
    SignalType
)

# Initialize strategies
long_div = LongBullishDivergenceStrategy(timeframe="15m")
short_div = ShortBearishDivergenceStrategy(timeframe="15m")
confluence_checker = APlusConfluenceChecker()

# Analyze for signals
long_signal = long_div.analyze(candles)
short_signal = short_div.analyze(candles)

# Validate with A+ checker
if long_signal:
    result = confluence_checker.check_confluence(
        candles=candles,
        signal_type=SignalType.LONG,
        open_interest=oi_data
    )

    if result.is_aplus:
        print(f"🚀 A+ LONG Signal!")
        print(f"Entry: {long_signal.price:.2f}")
        print(f"Stop Loss: {long_signal.stop_loss:.2f}")
        print(f"Take Profit: {long_signal.take_profit:.2f}")
        print(f"R/R Ratio: {long_signal.risk_reward_ratio:.1f}:1")
        print(f"Strength: {long_signal.strength.value}")
        print(f"Reasons: {long_signal.reasons}")
```

---

## FILES STRUCTURE

```
src/trading/
├── indicators/
│   ├── fibonacci.py                    # Fibonacci retracement
│   ├── volume_profile.py              # Volume profile analysis
│   ├── candlestick_patterns.py        # Candlestick pattern detector
│   ├── standard_deviation.py          # Bollinger Bands / Std Dev
│   └── head_and_shoulders.py          # H&S pattern detector
│
└── strategies/
    ├── long_bullish_divergence_strategy.py       # LONG #1
    ├── long_ema_bounce_strategy.py               # LONG #2
    ├── long_support_oi_buildup_strategy.py       # LONG #3
    ├── long_pivot_confluence_strategy.py         # LONG #4
    ├── long_fibonacci_accumulation_strategy.py   # LONG #5
    ├── short_bearish_divergence_strategy.py      # SHORT #1
    ├── short_ema_rejection_strategy.py           # SHORT #2
    ├── short_resistance_oi_buildup_strategy.py   # SHORT #3
    ├── short_head_shoulders_strategy.py          # SHORT #4
    ├── short_overextension_reversal_strategy.py  # SHORT #5
    └── aplus_confluence_checker.py               # A+ Checker
```

---

## NOTES

- All strategies automatically calculate stop loss and take profit levels
- Risk is limited to max 3% from entry (4% for major patterns like H&S)
- Default risk/reward ratios: 2:1 (some strategies use 2.5:1)
- Strategies return `TradingSignal` objects with full metadata
- Signal strength: WEAK, MEDIUM, STRONG, VERY_STRONG

---

## REFERENCES

Based on optimal entry strategies for crypto trading with confluence-based validation.
