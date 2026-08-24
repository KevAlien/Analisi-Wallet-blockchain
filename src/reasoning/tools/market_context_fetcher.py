"""
Market context fetcher
Retrieves current market conditions for context-aware analysis
"""
from typing import Dict, Any
import logging
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)


class MarketContextFetcher:
    """
    Fetches market context data

    Provides:
    - Current prices
    - Recent price changes
    - Volume data
    - Market sentiment indicators
    """

    def __init__(self):
        """Initialize market context fetcher"""
        self.client = httpx.AsyncClient(timeout=10)
        self.cache = {}
        self.cache_duration = 60  # Cache for 60 seconds

    async def get_context(self) -> Dict[str, Any]:
        """
        Get current market context

        Returns:
            Market context dict
        """
        # Check cache
        if self._is_cache_valid():
            return self.cache["data"]

        try:
            # Fetch ETH price from CoinGecko (free API, no key needed)
            eth_data = await self._fetch_eth_price()

            context = {
                "timestamp": datetime.now().isoformat(),
                "eth": eth_data,
                "market_conditions": self._determine_market_conditions(eth_data)
            }

            # Update cache
            self.cache = {
                "data": context,
                "timestamp": datetime.now()
            }

            return context

        except Exception as e:
            logger.error(f"Failed to fetch market context: {str(e)}")
            return self._get_fallback_context()

    async def _fetch_eth_price(self) -> Dict[str, Any]:
        """Fetch ETH price from CoinGecko"""
        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": "ethereum",
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_24hr_vol": "true"
            }

            response = await self.client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            eth = data.get("ethereum", {})

            return {
                "price_usd": eth.get("usd", 0),
                "change_24h": eth.get("usd_24h_change", 0),
                "volume_24h": eth.get("usd_24h_vol", 0)
            }

        except Exception as e:
            logger.warning(f"CoinGecko API error: {str(e)}")
            return {
                "price_usd": 0,
                "change_24h": 0,
                "volume_24h": 0,
                "error": str(e)
            }

    def _determine_market_conditions(self, eth_data: Dict) -> str:
        """
        Determine current market conditions

        Args:
            eth_data: ETH market data

        Returns:
            Market condition string
        """
        change_24h = eth_data.get("change_24h", 0)

        if change_24h > 5:
            return "strong_bullish"
        elif change_24h > 2:
            return "bullish"
        elif change_24h > -2:
            return "neutral"
        elif change_24h > -5:
            return "bearish"
        else:
            return "strong_bearish"

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if not self.cache or "timestamp" not in self.cache:
            return False

        age = (datetime.now() - self.cache["timestamp"]).total_seconds()
        return age < self.cache_duration

    def _get_fallback_context(self) -> Dict[str, Any]:
        """Get fallback context when API fails"""
        return {
            "timestamp": datetime.now().isoformat(),
            "eth": {
                "price_usd": 0,
                "change_24h": 0,
                "volume_24h": 0,
                "error": "Market data unavailable"
            },
            "market_conditions": "unknown"
        }

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
