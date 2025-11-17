#!/bin/bash
# Test runner script for Blockchain Wallet Analysis

echo "🧪 Running tests for Blockchain Wallet Analysis"
echo "================================================"
echo ""

# Set environment to disable plugin autoload to avoid compatibility issues
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

# Run tests with Python module pytest
python -m pytest tests/ -v --tb=short "$@"

echo ""
echo "================================================"
echo "✅ Test run complete!"
echo ""
echo "Tips:"
echo "  - Run specific test: ./run_tests.sh tests/test_basic_functionality.py"
echo "  - Run with coverage: ./run_tests.sh --cov=src"
echo "  - Run only unit tests: ./run_tests.sh tests/unit/"
