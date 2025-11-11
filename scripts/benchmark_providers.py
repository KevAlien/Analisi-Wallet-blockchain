"""
Benchmark script to compare LLM provider performance
"""
import asyncio
import sys
import time
import logging
from typing import Dict, List
from datetime import datetime

sys.path.insert(0, '/app')

from src.reasoning.llm_factory import LLMFactory
from src.config.llm_config import LLMConfig

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


async def benchmark_provider(provider_name: str) -> Dict:
    """Benchmark a single provider"""
    print(f"\n🔍 Benchmarking {provider_name.upper()}...")

    try:
        config = LLMConfig()
        config.provider = provider_name
        provider = LLMFactory.create_provider(config, enable_fallback=False)

        if not provider.is_available():
            return {"provider": provider_name, "available": False}

        # Test 1: Simple generation
        start = time.time()
        response1 = await provider.generate(
            prompt="Explain blockchain whales in one sentence.",
            temperature=0.7,
            max_tokens=50
        )
        latency1 = (time.time() - start) * 1000

        # Test 2: JSON generation
        start = time.time()
        schema = {
            "type": "object",
            "properties": {
                "signal_type": {"type": "string"},
                "confidence": {"type": "number"}
            }
        }
        response2 = await provider.generate_json(
            prompt="Generate a trading signal.",
            schema=schema
        )
        latency2 = (time.time() - start) * 1000

        # Test 3: Longer generation
        start = time.time()
        response3 = await provider.generate(
            prompt="Analyze this whale transaction: 500 ETH sent to Binance. Provide detailed reasoning.",
            temperature=0.7,
            max_tokens=500
        )
        latency3 = (time.time() - start) * 1000

        tokens_per_sec = response3.get("tokens_used", 0) / (latency3 / 1000) if latency3 > 0 else 0

        if hasattr(provider, 'close'):
            await provider.close()

        return {
            "provider": provider_name,
            "available": True,
            "simple_latency_ms": round(latency1, 2),
            "json_latency_ms": round(latency2, 2),
            "complex_latency_ms": round(latency3, 2),
            "tokens_per_sec": round(tokens_per_sec, 2),
            "context_window": provider.get_context_window()
        }

    except Exception as e:
        return {
            "provider": provider_name,
            "available": False,
            "error": str(e)
        }


async def main():
    """Run benchmarks"""
    print("\n" + "="*70)
    print("🏁 WHALE TRACKER LLM PROVIDER BENCHMARK")
    print("="*70)

    config = LLMConfig()
    providers = config.fallback_providers

    print(f"\n📋 Testing providers: {', '.join(providers)}")
    print(f"⏱️  This may take a few minutes...\n")

    results = []
    for provider in providers:
        result = await benchmark_provider(provider)
        results.append(result)
        await asyncio.sleep(1)

    # Display results
    print("\n" + "="*70)
    print("📊 BENCHMARK RESULTS")
    print("="*70)

    print(f"\n{'Provider':<15} {'Available':<12} {'Simple':<12} {'JSON':<12} {'Complex':<12} {'Tok/sec':<10}")
    print("-" * 70)

    for result in results:
        provider = result["provider"]
        available = "✅ Yes" if result.get("available") else "❌ No"

        if result.get("available"):
            simple = f"{result['simple_latency_ms']}ms"
            json_lat = f"{result['json_latency_ms']}ms"
            complex_lat = f"{result['complex_latency_ms']}ms"
            tok_sec = f"{result['tokens_per_sec']}"
        else:
            simple = json_lat = complex_lat = tok_sec = "N/A"

        print(f"{provider:<15} {available:<12} {simple:<12} {json_lat:<12} {complex_lat:<12} {tok_sec:<10}")

    # Recommendations
    print("\n" + "="*70)
    print("💡 RECOMMENDATIONS")
    print("="*70)

    available_results = [r for r in results if r.get("available")]

    if not available_results:
        print("\n❌ No providers available!")
        print("   Please configure at least one LLM provider.")
        return

    # Find fastest for simple tasks
    fastest_simple = min(available_results, key=lambda x: x.get("simple_latency_ms", float('inf')))
    print(f"\n⚡ Fastest (simple tasks): {fastest_simple['provider'].upper()}")
    print(f"   Latency: {fastest_simple['simple_latency_ms']}ms")

    # Find best tokens/sec
    best_throughput = max(available_results, key=lambda x: x.get("tokens_per_sec", 0))
    print(f"\n🚀 Best throughput: {best_throughput['provider'].upper()}")
    print(f"   Tokens/sec: {best_throughput['tokens_per_sec']}")

    # Find best context window
    best_context = max(available_results, key=lambda x: x.get("context_window", 0))
    print(f"\n📏 Largest context: {best_context['provider'].upper()}")
    print(f"   Context window: {best_context['context_window']} tokens")

    print("\n" + "="*70)
    print("✅ Benchmark complete!")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
