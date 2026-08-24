"""
Test script for LLM providers
"""
import asyncio
import sys
import logging
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, '/app')

from src.reasoning.llm_factory import LLMFactory
from src.config.llm_config import LLMConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_provider(provider_name: str, config: LLMConfig):
    """Test a single provider"""
    print(f"\n{'='*60}")
    print(f"Testing: {provider_name.upper()}")
    print(f"{'='*60}")

    try:
        # Create provider
        provider_config = LLMConfig()
        provider_config.provider = provider_name
        provider = LLMFactory.create_provider(provider_config, enable_fallback=False)

        # Check availability
        is_available = provider.is_available()
        print(f"✅ Available: {is_available}")

        if not is_available:
            print(f"❌ Provider {provider_name} is not available")
            return False

        print(f"📊 Provider: {provider.get_provider_name()}")
        print(f"📏 Context window: {provider.get_context_window()} tokens")

        # Test generation
        print(f"\n🧪 Testing text generation...")
        start_time = datetime.now()

        response = await provider.generate(
            prompt="Explain what a blockchain whale is in one sentence.",
            temperature=0.7,
            max_tokens=100
        )

        latency = response.get("latency_ms", 0)
        content = response.get("content", "")
        tokens = response.get("tokens_used", 0)

        print(f"⏱️  Latency: {latency}ms")
        print(f"🎯 Tokens used: {tokens}")
        print(f"📝 Response: {content[:200]}...")

        # Test JSON generation
        print(f"\n🧪 Testing JSON generation...")

        schema = {
            "type": "object",
            "properties": {
                "signal_type": {"type": "string"},
                "confidence": {"type": "number"}
            }
        }

        json_response = await provider.generate_json(
            prompt="Generate a trading signal for a 500 ETH whale transaction.",
            schema=schema
        )

        parsed = json_response.get("parsed_json", {})
        print(f"📦 Parsed JSON: {parsed}")

        # Close provider
        if hasattr(provider, 'close'):
            await provider.close()

        print(f"\n✅ {provider_name.upper()} test PASSED")
        return True

    except Exception as e:
        print(f"\n❌ {provider_name.upper()} test FAILED: {str(e)}")
        return False


async def test_all_providers():
    """Test all configured providers"""
    print("\n" + "="*60)
    print("🧪 SENTRYCAGE LLM PROVIDER TEST SUITE")
    print("="*60)

    config = LLMConfig()

    print(f"\n📋 Configuration:")
    print(f"  Primary provider: {config.provider}")
    print(f"  Reasoning enabled: {config.enable_reasoning}")
    print(f"  Fallback chain: {' -> '.join(config.fallback_providers)}")

    # Test each provider in fallback chain
    results = {}

    for provider_name in config.fallback_providers:
        try:
            result = await test_provider(provider_name, config)
            results[provider_name] = result
        except Exception as e:
            logger.error(f"Error testing {provider_name}: {str(e)}")
            results[provider_name] = False

        # Small delay between tests
        await asyncio.sleep(1)

    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)

    for provider, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {provider:20} {status}")

    passed_count = sum(1 for p in results.values() if p)
    total_count = len(results)

    print(f"\nTotal: {passed_count}/{total_count} providers available")

    if passed_count == 0:
        print("\n⚠️  WARNING: No LLM providers are available!")
        print("  The app will run in rule-based mode only.")
        return False

    print(f"\n✅ At least one provider is available!")
    print(f"   Primary: {config.provider}")

    return True


async def main():
    """Main test function"""
    try:
        success = await test_all_providers()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
