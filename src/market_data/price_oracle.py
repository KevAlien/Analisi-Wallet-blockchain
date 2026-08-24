"""
Price Oracle for fetching cryptocurrency market data from multiple sources.

Supported providers:
- CoinGecko (free tier)
- Binance
- Hyperliquid (public info API)
- Generic fallback
"""
import httpx
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import logging

from ..trading.indicators import Candle


logger = logging.getLogger(__name__)


class PriceSource(Enum):
    """Supported price data sources."""
    COINGECKO = "coingecko"
    BINANCE = "binance"
    COINBASE = "coinbase"
    HYPERLIQUID = "hyperliquid"


class PriceOracle:
    """Fetches price and candle data from multiple sources."""

    def __init__(self, primary_source: PriceSource = PriceSource.COINGECKO,
                 cache_ttl: int = 60):
        """
        Initialize Price Oracle.

        Args:
            primary_source: Primary data source to use
            cache_ttl: Cache time-to-live in seconds (default: 60)
        """
        self.primary_source = primary_source
        self.cache_ttl = cache_ttl
        self.cache: Dict[str, Dict[str, Any]] = {}

        # API endpoints
        self.coingecko_base = "https://api.coingecko.com/api/v3"
        self.binance_base = "https://api.binance.com/api/v3"
        self.coinbase_base = "https://api.coinbase.com/v2"
        self.hyperliquid_base = "https://api.hyperliquid.xyz/info"

    async def get_current_price(self, symbol: str, vs_currency: str = "usd") -> Optional[float]:
        """
        Get current price for a symbol.

        Args:
            symbol: Cryptocurrency symbol (e.g., "bitcoin", "ethereum")
            vs_currency: Quote currency (default: "usd")

        Returns:
            Current price or None if error
        """
        cache_key = f"{symbol}_{vs_currency}_price"

        # Check cache
        if self._is_cached(cache_key):
            return self.cache[cache_key]['data']

        try:
            if self.primary_source == PriceSource.COINGECKO:
                price = await self._fetch_coingecko_price(symbol, vs_currency)
            elif self.primary_source == PriceSource.BINANCE:
                price = await self._fetch_binance_price(symbol, vs_currency)
            elif self.primary_source == PriceSource.HYPERLIQUID:
                price = await self._fetch_hyperliquid_price(symbol)
            else:
                price = await self._fetch_coingecko_price(symbol, vs_currency)

            if price:
                self._cache_data(cache_key, price)

            return price

        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return None

    async def get_historical_candles(self, symbol: str, interval: str = "1h",
                                    limit: int = 100) -> List[Candle]:
        """
        Get historical OHLCV candles.

        Args:
            symbol: Trading pair (e.g., "BTCUSDT" for Binance, "bitcoin" for CoinGecko)
            interval: Candle interval (e.g., "1m", "5m", "15m", "1h", "4h", "1d")
            limit: Number of candles to fetch (default: 100)

        Returns:
            List of Candle objects
        """
        cache_key = f"{symbol}_{interval}_candles_{limit}"

        # Check cache (shorter TTL for candles)
        if self._is_cached(cache_key, ttl=30):
            return self.cache[cache_key]['data']

        try:
            if self.primary_source == PriceSource.BINANCE:
                candles = await self._fetch_binance_candles(symbol, interval, limit)
            elif self.primary_source == PriceSource.COINGECKO:
                candles = await self._fetch_coingecko_candles(symbol, interval, limit)
            else:
                candles = await self._fetch_binance_candles(symbol, interval, limit)

            if candles:
                self._cache_data(cache_key, candles, ttl=30)

            return candles

        except Exception as e:
            logger.error(f"Error fetching candles for {symbol}: {e}")
            return []

    async def _fetch_coingecko_price(self, symbol: str, vs_currency: str) -> Optional[float]:
        """Fetch price from CoinGecko API."""
        url = f"{self.coingecko_base}/simple/price"
        params = {
            'ids': symbol.lower(),
            'vs_currencies': vs_currency.lower()
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            if symbol.lower() in data:
                return float(data[symbol.lower()][vs_currency.lower()])

        return None

    async def _fetch_binance_price(self, symbol: str, vs_currency: str = "USDT") -> Optional[float]:
        """Fetch price from Binance API."""
        # Convert symbol to Binance format (e.g., BTC -> BTCUSDT)
        ticker = f"{symbol.upper()}{vs_currency.upper()}"
        url = f"{self.binance_base}/ticker/price"
        params = {'symbol': ticker}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            return float(data['price'])

    async def _fetch_hyperliquid_price(self, symbol: str) -> Optional[float]:
        """Fetch mid price from Hyperliquid public info API.

        Uses the allMids endpoint which returns a dict of coin -> mid price string.
        Symbol should be the base asset (e.g. "BTC", "ETH") — USDT suffix is stripped.
        """
        coin = symbol.upper().replace("USDT", "").replace("USD", "")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.hyperliquid_base,
                json={"type": "allMids"},
                timeout=10.0,
            )
            response.raise_for_status()
            mids: Dict[str, str] = response.json()
            raw = mids.get(coin)
            if raw is None:
                logger.warning(f"Hyperliquid: coin '{coin}' non trovato in allMids")
                return None
            return float(raw)

    async def _fetch_coingecko_candles(self, symbol: str, interval: str, limit: int) -> List[Candle]:
        """
        Fetch OHLC candles from CoinGecko API.

        Note: CoinGecko free tier has limited OHLC data.
        """
        # Map interval to days (CoinGecko uses days parameter)
        days_map = {
            '1m': 1,
            '5m': 1,
            '15m': 1,
            '1h': 7,
            '4h': 30,
            '1d': 90
        }
        days = days_map.get(interval, 7)

        url = f"{self.coingecko_base}/coins/{symbol.lower()}/ohlc"
        params = {
            'vs_currency': 'usd',
            'days': days
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=15.0)
            response.raise_for_status()
            data = response.json()

            candles = []
            for item in data[-limit:]:  # Get last 'limit' candles
                # CoinGecko OHLC format: [timestamp, open, high, low, close]
                timestamp = datetime.fromtimestamp(item[0] / 1000)
                candles.append(Candle(
                    timestamp=timestamp,
                    open=float(item[1]),
                    high=float(item[2]),
                    low=float(item[3]),
                    close=float(item[4]),
                    volume=0.0  # CoinGecko free tier doesn't provide volume in OHLC
                ))

            return candles

    async def _fetch_binance_candles(self, symbol: str, interval: str, limit: int) -> List[Candle]:
        """Fetch OHLCV candles from Binance API."""
        url = f"{self.binance_base}/klines"
        params = {
            'symbol': symbol.upper(),
            'interval': interval,
            'limit': limit
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=15.0)
            response.raise_for_status()
            data = response.json()

            candles = []
            for item in data:
                # Binance kline format:
                # [open_time, open, high, low, close, volume, close_time, ...]
                timestamp = datetime.fromtimestamp(item[0] / 1000)
                candles.append(Candle(
                    timestamp=timestamp,
                    open=float(item[1]),
                    high=float(item[2]),
                    low=float(item[3]),
                    close=float(item[4]),
                    volume=float(item[5])
                ))

            return candles

    def _is_cached(self, key: str, ttl: Optional[int] = None) -> bool:
        """Check if data is in cache and still valid."""
        if key not in self.cache:
            return False

        cache_ttl = ttl if ttl is not None else self.cache_ttl
        age = (datetime.now() - self.cache[key]['timestamp']).total_seconds()

        return age < cache_ttl

    def _cache_data(self, key: str, data: Any, ttl: Optional[int] = None):
        """Cache data with timestamp."""
        self.cache[key] = {
            'data': data,
            'timestamp': datetime.now(),
            'ttl': ttl if ttl is not None else self.cache_ttl
        }

    def clear_cache(self):
        """Clear all cached data."""
        self.cache = {}

    async def get_multiple_prices(self, symbols: List[str], vs_currency: str = "usd") -> Dict[str, float]:
        """
        Get prices for multiple symbols concurrently.

        Args:
            symbols: List of cryptocurrency symbols
            vs_currency: Quote currency

        Returns:
            Dictionary mapping symbol to price
        """
        tasks = [self.get_current_price(symbol, vs_currency) for symbol in symbols]
        prices = await asyncio.gather(*tasks, return_exceptions=True)

        result = {}
        for symbol, price in zip(symbols, prices):
            if not isinstance(price, Exception) and price is not None:
                result[symbol] = price

        return result

    async def get_24h_stats(self, symbol: str) -> Optional[Dict[str, float]]:
        """
        Get 24-hour statistics (change, volume, high, low).

        Args:
            symbol: Trading pair symbol

        Returns:
            Dictionary with 24h stats or None if error
        """
        try:
            if self.primary_source == PriceSource.BINANCE:
                return await self._fetch_binance_24h_stats(symbol)
            else:
                # Fallback: calculate from candles
                candles = await self.get_historical_candles(symbol, "1h", 24)
                if not candles:
                    return None

                return {
                    'high_24h': max(c.high for c in candles),
                    'low_24h': min(c.low for c in candles),
                    'volume_24h': sum(c.volume for c in candles),
                    'price_change_24h': ((candles[-1].close - candles[0].open) / candles[0].open) * 100
                }

        except Exception as e:
            logger.error(f"Error fetching 24h stats for {symbol}: {e}")
            return None

    async def _fetch_binance_24h_stats(self, symbol: str) -> Dict[str, float]:
        """Fetch 24h statistics from Binance."""
        url = f"{self.binance_base}/ticker/24hr"
        params = {'symbol': symbol.upper()}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            return {
                'high_24h': float(data['highPrice']),
                'low_24h': float(data['lowPrice']),
                'volume_24h': float(data['volume']),
                'price_change_24h': float(data['priceChangePercent'])
            }
