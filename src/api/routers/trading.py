"""
Trading endpoints: strategies, signals, backtest, execution.
"""
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException, Depends, Query

from src.api.auth.security import get_current_user, check_rate_limit, check_tier_permission
from src.api.models.schemas import (
    StrategyInfo, StrategyListResponse, TradingSignalResponse,
    BacktestRequest, BacktestResponse,
    TradeExecuteRequest, TradeExecuteResponse,
    Tier, UsageLimits,
)
from src.database import mongodb as db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/trading", tags=["Trading"])

# Strategy catalog
STRATEGIES = [
    StrategyInfo(
        name="EMA_CROSSOVER",
        description="EMA Crossover with Heikin Ashi confirmation. Trend-following strategy.",
        timeframes=["1h", "4h"],
        min_rr_ratio=2.0,
        win_rate_target="50%+",
        requires_tier=Tier.FREE,
    ),
    StrategyInfo(
        name="RSI_DIVERGENCE",
        description="RSI Divergence day trading. Identifies bullish/bearish divergences.",
        timeframes=["5m", "15m"],
        min_rr_ratio=2.5,
        win_rate_target="45%+",
        requires_tier=Tier.FREE,
    ),
    StrategyInfo(
        name="SCALPING_TRIPLE",
        description="Scalping with Pivot Points + Stochastic RSI + VWAP triple confluence.",
        timeframes=["15m", "30m"],
        min_rr_ratio=2.0,
        win_rate_target="55%+",
        requires_tier=Tier.PRO,
    ),
    StrategyInfo(
        name="DIVERGENCE_DETECTOR",
        description="Multi-oscillator divergence detection across timeframes.",
        timeframes=["1h", "4h"],
        min_rr_ratio=3.0,
        win_rate_target="40%+",
        requires_tier=Tier.PRO,
    ),
    StrategyInfo(
        name="OPEN_INTEREST",
        description="Open Interest analysis for futures sentiment and positioning.",
        timeframes=["15m", "1h"],
        min_rr_ratio=2.0,
        win_rate_target="50%+",
        requires_tier=Tier.PRO,
    ),
    StrategyInfo(
        name="LONG_BULLISH_DIVERGENCE",
        description="Bullish divergence + confirmations. Price LL, RSI HL, volume expansion.",
        timeframes=["15m", "1h"],
        min_rr_ratio=2.5,
        win_rate_target="60-75%",
        requires_tier=Tier.PRO,
    ),
    StrategyInfo(
        name="LONG_EMA_BOUNCE",
        description="EMA 200/50 bounce + rejection candle. Trend continuation LONG.",
        timeframes=["1h", "4h"],
        min_rr_ratio=2.0,
        win_rate_target="60-75%",
        requires_tier=Tier.PRO,
    ),
    StrategyInfo(
        name="LONG_SUPPORT_OI_BUILDUP",
        description="Key support + increasing Open Interest buildup. Intraday breakout LONG.",
        timeframes=["15m", "1h"],
        min_rr_ratio=2.0,
        win_rate_target="60-75%",
        requires_tier=Tier.PRO,
    ),
    StrategyInfo(
        name="LONG_PIVOT_CONFLUENCE",
        description="S1/S2 pivot + Stochastic RSI crossover + VWAP break. Triple confluence LONG.",
        timeframes=["15m", "30m"],
        min_rr_ratio=2.0,
        win_rate_target="60-75%",
        requires_tier=Tier.PRO,
    ),
    StrategyInfo(
        name="LONG_FIBONACCI_ACCUMULATION",
        description="Golden zone (0.618-0.786) retracement + consolidation + breakout.",
        timeframes=["1h", "4h"],
        min_rr_ratio=2.5,
        win_rate_target="60-75%",
        requires_tier=Tier.PRO,
    ),
    StrategyInfo(
        name="SHORT_BEARISH_DIVERGENCE",
        description="Bearish divergence + support breakdown. Price HH, RSI LH, volume confirmation.",
        timeframes=["15m", "1h"],
        min_rr_ratio=2.5,
        win_rate_target="60-75%",
        requires_tier=Tier.PRO,
    ),
    StrategyInfo(
        name="SHORT_EMA_REJECTION",
        description="EMA 200 rejection + Death Cross + local support break. Trend reversal SHORT.",
        timeframes=["1h", "4h"],
        min_rr_ratio=2.0,
        win_rate_target="60-75%",
        requires_tier=Tier.PRO,
    ),
    StrategyInfo(
        name="SHORT_RESISTANCE_OI_BUILDUP",
        description="Multi-touch resistance + OI increase + price declining. SHORT on support break.",
        timeframes=["15m", "1h"],
        min_rr_ratio=2.0,
        win_rate_target="60-75%",
        requires_tier=Tier.PRO,
    ),
    StrategyInfo(
        name="SHORT_HEAD_SHOULDERS",
        description="Classic Head & Shoulders pattern. Neckline break + failed retest SHORT.",
        timeframes=["1h", "4h"],
        min_rr_ratio=2.5,
        win_rate_target="60-75%",
        requires_tier=Tier.PRO,
    ),
    StrategyInfo(
        name="SHORT_OVEREXTENSION_REVERSAL",
        description=">3 std dev above MA + RSI >70 + reversal candle. Mean reversion SHORT.",
        timeframes=["15m", "1h"],
        min_rr_ratio=2.0,
        win_rate_target="60-75%",
        requires_tier=Tier.PRO,
    ),
    StrategyInfo(
        name="DISTRIBUTION_SHORT",
        description="On-chain distribution detection + technical confirmation SHORT.",
        timeframes=["1h", "4h"],
        min_rr_ratio=2.0,
        win_rate_target="55%+",
        requires_tier=Tier.ENTERPRISE,
    ),
]


@router.get("/strategies", response_model=StrategyListResponse)
async def list_strategies(user: Dict[str, Any] = Depends(get_current_user)):
    """
    List all available trading strategies with their requirements.

    Strategies are filtered by the user's subscription tier.
    """
    await check_rate_limit(user)
    tier = Tier(user.get("tier", "free"))
    tier_order = {Tier.FREE: 0, Tier.PRO: 1, Tier.ENTERPRISE: 2}

    available = [
        s for s in STRATEGIES
        if tier_order[tier] >= tier_order[s.requires_tier]
    ]

    return StrategyListResponse(
        strategies=STRATEGIES,  # Show all, but mark which are available
        enabled_count=len(available),
    )


@router.get("/signals", response_model=List[TradingSignalResponse])
async def get_trading_signals(
    symbols: str = Query("BTCUSDT,ETHUSDT", description="Comma-separated symbols"),
    min_confidence: float = Query(0.5, ge=0, le=1),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get current trading signals from active strategies.

    Returns the latest signals generated by the trading engine.
    Perfect for AI agents to consume and act upon.
    """
    await check_rate_limit(user)

    symbol_list = [s.strip() for s in symbols.split(",")]

    signals, _ = await db.get_signals(
        user_id=str(user["_id"]),
        min_confidence=min_confidence,
        page=1,
        page_size=20,
    )

    results = []
    for sig in signals:
        if sig.get("source") in ["trading_bot", "strategy"] or sig.get("symbol") in symbol_list:
            results.append(TradingSignalResponse(
                id=str(sig["_id"]),
                symbol=sig.get("symbol", sig.get("chain", "UNKNOWN")),
                signal_type=sig.get("signal_type", "unknown"),
                strength=sig.get("strength", "medium"),
                confidence=sig.get("confidence", 0.0),
                entry_price=sig.get("entry_price"),
                stop_loss=sig.get("stop_loss"),
                take_profit=sig.get("take_profit"),
                strategy_name=sig.get("strategy_name", "unknown"),
                reasons=sig.get("reasoning_chain", []),
                created_at=sig.get("created_at", datetime.utcnow()),
            ))

    return results


@router.post("/backtest", response_model=BacktestResponse)
async def run_backtest(
    body: BacktestRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Run a backtest on a strategy with historical data.

    Requires Pro tier or above.
    """
    await check_rate_limit(user)
    await check_tier_permission(user, Tier.PRO)

    # Placeholder backtest - in production, this would use the actual backtesting framework
    logger.info(f"Backtest requested: {body.strategy} on {body.symbol}")

    return BacktestResponse(
        strategy=body.strategy,
        symbol=body.symbol,
        total_trades=0,
        win_rate=0.0,
        total_pnl=0.0,
        max_drawdown=0.0,
        sharpe_ratio=None,
        profit_factor=None,
    )


@router.post("/execute", response_model=TradeExecuteResponse)
async def execute_trade(
    body: TradeExecuteRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Execute or simulate a trade.

    - **dry_run=true**: Simulate only, track in paper portfolio
    - **dry_run=false**: Execute on connected exchange (Enterprise tier)

    AI agents can use this to execute trades based on signals.
    """
    await check_rate_limit(user)

    if not body.dry_run:
        await check_tier_permission(user, Tier.ENTERPRISE)

    trade_id = f"trade_{uuid.uuid4().hex[:12]}"
    user_id = str(user["_id"])

    # Store the trade
    trade_data = {
        "trade_id": trade_id,
        "symbol": body.symbol,
        "side": body.side.value,
        "size_pct": body.size_pct,
        "stop_loss_pct": body.stop_loss_pct,
        "take_profit_pct": body.take_profit_pct,
        "dry_run": body.dry_run,
        "status": "simulated" if body.dry_run else "pending",
        "entry_price": 0.0,  # Would be filled by market data
    }

    await db.store_trade(user_id, trade_data)
    logger.info(f"Trade {'simulated' if body.dry_run else 'executed'}: {trade_id}")

    return TradeExecuteResponse(
        trade_id=trade_id,
        symbol=body.symbol,
        side=body.side.value,
        entry_price=trade_data["entry_price"],
        size=body.size_pct,
        stop_loss=None,
        take_profit=None,
        dry_run=body.dry_run,
        status=trade_data["status"],
    )
