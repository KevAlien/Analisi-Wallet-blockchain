# How to Fix Test Fixtures - Explained

## The Problem

Tests were failing because **fixtures didn't match the data structure the code expects**.

## What Happened

### The Flow:
```
Raw Transaction → TransactionAnalyzer → Analyzed Transaction → SignalGenerator → Signals
```

### The Issue:
Our test fixtures were **raw transactions**, but the SignalGenerator expects **analyzed transactions**.

## The Solution: Proper Fixture Structure

### ❌ Old (Broken) Fixture
```python
@pytest.fixture
def sample_transaction():
    return {
        "hash": "0x123...",
        "from": "0xabc...",
        "to": "0x456...",
        "value": "1000000000000000000",  # Just wei
        "chain": "ethereum"
        # Missing: direction, is_significant, wallet_info, etc.
    }
```

**Tests using this would fail** because SignalGenerator checks for:
- `analyzed_tx.get('direction')` → Would be `None`
- `analyzed_tx.get('to_wallet_info')` → Would be `None`
- `analyzed_tx.get('is_significant')` → Would be `None` (treated as False)

### ✅ New (Working) Fixture
```python
@pytest.fixture
def analyzed_accumulation_transaction(sample_whale_address):
    """Transaction that's already been through the analyzer"""
    return {
        # Original transaction fields
        "hash": "0x123...",
        "from": "0xabc...",
        "to": sample_whale_address,
        "value": "500000000000000000000",
        "chain": "ethereum",

        # Fields added by TransactionAnalyzer
        "value_eth": 500.0,  # ← Converted from wei
        "is_significant": True,  # ← Threshold check
        "direction": "incoming",  # ← Flow direction
        "transaction_type": "transfer",
        "type_confidence": 0.9,

        # Wallet information ← THIS IS KEY!
        "from_wallet_info": None,
        "to_wallet_info": {
            "address": sample_whale_address,
            "name": "Test Whale",
            "category": "whale",
            "tags": ["test", "whale"]
        }
    }
```

## How the Code Uses These Fields

### SignalGenerator Logic:
```python
def generate_signals(self, analyzed_transaction):
    # Checks if significant first
    if not analyzed_transaction.get("is_significant", False):
        return []  # ← Old fixtures failed here!

    # Gets direction
    direction = analyzed_transaction.get("direction")

    # Gets wallet info based on direction
    if direction == "incoming":
        wallet_info = analyzed_transaction.get("to_wallet_info")  # ← Needs this!

    elif direction == "outgoing":
        wallet_info = analyzed_transaction.get("from_wallet_info")  # ← Or this!

    # Creates signal with wallet data
    return Signal(
        wallet_address=wallet_info.get("address"),  # ← Would crash without wallet_info
        wallet_name=wallet_info.get("name"),
        wallet_category=wallet_info.get("category"),
        # ...
    )
```

## Key Lessons

### 1. **Match Your Fixtures to the Real Data Flow**
Don't create simplified test data that skips processing steps.

### 2. **Analyze the Code to Understand Requirements**
Look at what fields the code actually uses:
```python
# In signal_generator.py line 142:
if not analyzed_transaction.get("is_significant", False):
    return signals  # ← Needs this field!

# Line 146:
direction = analyzed_transaction.get("direction")  # ← Needs this!

# Line 153:
wallet_info = analyzed_transaction.get("to_wallet_info", {})  # ← And this!
```

### 3. **Create Fixtures at the Right Level**
- `sample_transaction` → For testing the **analyzer**
- `analyzed_*_transaction` → For testing **signal generator** and **pipeline**

## How to Create Fixtures for Different Test Levels

### Testing TransactionAnalyzer
```python
def test_analyzer(sample_transaction):
    # Use raw transaction - analyzer adds the fields
    result = analyzer.analyze_transaction(sample_transaction)
    assert result["is_significant"]  # Check analyzer output
```

### Testing SignalGenerator
```python
def test_signal_gen(analyzed_accumulation_transaction):
    # Use pre-analyzed transaction with all fields
    signals = generator.generate_signals(analyzed_accumulation_transaction)
    assert len(signals) > 0  # Now it works!
```

### Testing Full Pipeline
```python
def test_full_pipeline(sample_transaction):
    # Start with raw, go through all steps
    analyzed = analyzer.analyze_transaction(sample_transaction)
    signals = generator.generate_signals(analyzed)
    assert len(signals) > 0
```

## Quick Reference: Required Fields by Component

### TransactionAnalyzer Expects (Input):
- `hash`, `from`, `to`, `value` (wei string)
- `blockNumber`, `timeStamp`, `chain`

### TransactionAnalyzer Produces (Output):
- **All input fields** +
- `value_eth` (float)
- `is_significant` (bool)
- `direction` ("incoming" | "outgoing" | "internal")
- `transaction_type`, `type_confidence`
- `from_wallet_info`, `to_wallet_info` (dict or None)

### SignalGenerator Expects (Input):
- **TransactionAnalyzer output** (all fields above)
- Specifically needs: `is_significant`, `direction`, `*_wallet_info`

## Result

✅ **Before**: 22/30 passing (73%)
✅ **After**: 29/30 passing (97%)

The one skipped test requires an RPC node connection, which is expected for unit tests.
