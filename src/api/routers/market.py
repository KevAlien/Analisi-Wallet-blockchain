"""
Market data endpoints: prices, candles, 24h stats.
"""
import logging
from datetime import datetime
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException, Depends, Query

from src.api.auth.security import get_current_user, check_rate_limit
from src.api.models.schemas import PriceResponse, CandleResponse
from src.market_data.price_oracle import PriceOracle, PriceSource

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/market", tags=["Market Data"])

# Shared instance
_oracle: PriceOracle = None


def _get_oracle() -> PriceOracle:
    global _oracle
    if _oracle is None:
        _oracle = PriceOracle(primary_source=PriceSource.BINANCE)
    return _oracle


@router.get("/prices", response_model=List[PriceResponse])
async def get_prices(
    symbols: str = Query("bitcoin,ethereum", description="Comma-separated symbols"),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get current prices for multiple symbols.

    Supports CoinGecko IDs (bitcoin, ethereum) or Binance pairs (BTCUSDT).
    """
    await check_rate_limit(user)
    oracle = _get_oracle()

    symbol_list = [s.strip() for s in symbols.split(",")]
    prices = await oracle.get_multiple_prices(symbol_list)

    results = []
    for symbol, price in prices.items():
        stats = await oracle.get_24h_stats(symbol.upper() + "USDT")
        results.append(PriceResponse(
            symbol=symbol,
            price=price,
            change_24h=stats.get("price_change_24h") if stats else None,
            volume_24h=stats.get("volume_24h") if stats else None,
            timestamp=datetime.utcnow(),
        ))

    return results


@router.get("/candles", response_model=List[CandleResponse])
async def get_candles(
    symbol: str = Query("BTCUSDT", description="Trading pair"),
    interval: str = Query("15m", description="Candle interval"),
    limit: int = Query(100, ge=1, le=500),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get OHLCV candlestick data.

    Intervals: 1m, 5m, 15m, 30m, 1h, 4h, 1d
    """
    await check_rate_limit(user)
    oracle = _get_oracle()

    candles = await oracle.get_historical_candles(symbol, interval, limit)

    if not candles:
        raise HTTPException(status_code=404, detail=f"No candle data for {symbol}")

    return [
        CandleResponse(
            timestamp=c.timestamp,
            open=c.open,
            high=c.high,
            low=c.low,
            close=c.close,
            volume=c.volume,
        )
        for c in candles
    ]
