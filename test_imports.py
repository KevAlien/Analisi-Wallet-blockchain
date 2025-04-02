#!/usr/bin/env python3
"""
Test script to verify imports are working correctly.
"""
import sys
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print("\nTesting imports...")

# Test telegram imports
try:
    from telegram import Bot
    from telegram.constants import ParseMode
    print("✓ Telegram imports successful")
except ImportError as e:
    print(f"✗ Telegram import error: {e}")

# Test web3 imports
try:
    from web3 import Web3
    print("✓ Web3 imports successful")
except ImportError as e:
    print(f"✗ Web3 import error: {e}")

# Test dotenv imports
try:
    from dotenv import load_dotenv
    print("✓ python-dotenv imports successful")
except ImportError as e:
    print(f"✗ python-dotenv import error: {e}")

print("\nTest complete.")
