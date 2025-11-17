# Testing Guide

This document describes how to run and write tests for the Blockchain Wallet Analysis project.

## Quick Start

### Running All Tests

```bash
./run_tests.sh
```

Or using pytest directly:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/ -v
```

### Running Specific Tests

```bash
# Run only basic functionality tests
./run_tests.sh tests/test_basic_functionality.py

# Run only unit tests
./run_tests.sh tests/unit/

# Run only integration tests
./run_tests.sh tests/integration/

# Run a specific test
./run_tests.sh tests/unit/test_config.py::TestConfiguration::test_wallet_registry_loaded
```

### Running with Coverage

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/ --cov=src --cov-report=html
```

Then open `htmlcov/index.html` in your browser to view the coverage report.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures and configuration
├── test_basic_functionality.py  # Smoke tests
├── unit/                    # Unit tests
│   ├── test_config.py
│   ├── test_signal_generator.py
│   └── test_transaction_analyzer.py
└── integration/             # Integration tests
    └── test_signal_pipeline.py
```

## Test Categories

### Unit Tests
Located in `tests/unit/`, these test individual components in isolation:
- Configuration loading
- Signal generation logic
- Transaction analysis
- Individual utilities

### Integration Tests
Located in `tests/integration/`, these test multiple components working together:
- Complete signal pipeline (transaction → analysis → signal)
- Notification system integration
- End-to-end workflows

### Basic Functionality Tests
Located in `tests/test_basic_functionality.py`, these are smoke tests that verify:
- All modules can be imported
- Core components can be instantiated
- Basic configuration is valid

## Current Test Results

As of the latest run:
- ✅ **22 tests passing**
- ⚠️ **1 test skipped** (requires RPC node)
- ❌ **7 tests failing** (require fixture updates)

### Passing Tests Include:
- ✅ Module imports
- ✅ Configuration loading
- ✅ Wallet registry validation
- ✅ Transaction analysis
- ✅ Component instantiation

### Known Issues:
- Some signal generator tests need updated fixtures with proper wallet info
- Async tests require pytest-asyncio plugin (currently disabled for compatibility)

## Writing New Tests

### Example Unit Test

```python
import pytest
from src.signals.signal_generator import SignalGenerator

class TestMyFeature:
    def setup_method(self):
        """Setup runs before each test"""
        self.generator = SignalGenerator()

    def test_basic_functionality(self):
        """Test description"""
        result = self.generator.some_method()
        assert result is not None
```

### Using Fixtures

Fixtures are defined in `tests/conftest.py`. Use them like this:

```python
def test_with_fixture(sample_transaction, mock_telegram_bot):
    """Test using shared fixtures"""
    # Use the fixtures
    assert sample_transaction['hash'] is not None
```

### Available Fixtures

- `mock_env_vars` - Mock environment variables
- `sample_transaction` - Sample transaction data
- `sample_whale_address` - Example whale wallet address
- `sample_exchange_address` - Example exchange address
- `mock_telegram_bot` - Mocked Telegram bot
- `mock_blockchain_client` - Mocked blockchain client

## Important Notes

### Web3 Plugin Compatibility

Due to a compatibility issue with the web3 pytest plugin, you must set:

```bash
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
```

This is automatically done in the `run_tests.sh` script.

### Environment Variables

Tests use mocked environment variables by default (from the `mock_env_vars` fixture). If you need to test with real API keys, create a `.env.test` file and load it manually.

### Async Tests

Currently, async tests are not fully supported due to the pytest-asyncio compatibility issue. For now, async functionality is tested through integration tests or by running the application in test mode:

```bash
python main.py --test
```

## Continuous Improvement

The test suite is a work in progress. Contributions welcome!

### TODO:
- [ ] Fix signal generator test fixtures
- [ ] Add async test support
- [ ] Increase code coverage to >80%
- [ ] Add performance tests
- [ ] Add end-to-end tests with mocked blockchain
