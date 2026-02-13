"""
Portfolio management endpoints.
"""
import logging
from datetime import datetime
from typing import Dict, Any, List

from fastapi import APIRouter, Depends, Query

from src.api.auth.security import get_current_user, check_rate_limit
from src.api.models.schemas import PositionResponse, PortfolioResponse
from src.database import mongodb as db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


@router.get("", response_model=PortfolioResponse)
async def get_portfolio(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get portfolio overview including capital, PnL, and open positions.

    Useful for AI agents to assess current exposure before trading.
    """
    await check_rate_limit(user)
    user_id = str(user["_id"])

    # Get all trades
    trades, total = await db.get_trades(user_id, page=1, page_size=1000)

    initial_capital = user.get("settings", {}).get("initial_capital", 10000.0)
    open_positions = []
    total_pnl = 0.0
    wins = 0
    closed_trades = 0

    for trade in trades:
        if trade.get("status") == "open":
            open_positions.append(PositionResponse(
                symbol=trade.get("symbol", "UNKNOWN"),
                side=trade.get("side", "LONG"),
                entry_price=trade.get("entry_price", 0),
                current_price=trade.get("current_price"),
                size=trade.get("size_pct", 0),
                pnl=trade.get("pnl"),
                pnl_pct=trade.get("pnl_pct"),
                stop_loss=trade.get("stop_loss"),
                take_profit=trade.get("take_profit"),
                entry_time=trade.get("created_at", datetime.utcnow()),
                status="open",
            ))
        elif trade.get("status") == "closed":
            pnl = trade.get("pnl", 0)
            total_pnl += pnl
            closed_trades += 1
            if pnl > 0:
                wins += 1

    current_capital = initial_capital + total_pnl
    win_rate = (wins / closed_trades * 100) if closed_trades > 0 else 0.0
    total_return = (total_pnl / initial_capital * 100) if initial_capital > 0 else 0.0

    return PortfolioResponse(
        initial_capital=initial_capital,
        current_capital=current_capital,
        total_pnl=total_pnl,
        total_return_pct=total_return,
        open_positions=open_positions,
        total_trades=total,
        win_rate=win_rate,
    )


@router.get("/positions", response_model=List[PositionResponse])
async def get_open_positions(user: Dict[str, Any] = Depends(get_current_user)):
    """Get all currently open positions."""
    await check_rate_limit(user)
    user_id = str(user["_id"])

    trades, _ = await db.get_trades(user_id, status="open", page=1, page_size=100)

    return [
        PositionResponse(
            symbol=t.get("symbol", "UNKNOWN"),
            side=t.get("side", "LONG"),
            entry_price=t.get("entry_price", 0),
            current_price=t.get("current_price"),
            size=t.get("size_pct", 0),
            pnl=t.get("pnl"),
            pnl_pct=t.get("pnl_pct"),
            stop_loss=t.get("stop_loss"),
            take_profit=t.get("take_profit"),
            entry_time=t.get("created_at", datetime.utcnow()),
            status="open",
        )
        for t in trades
    ]


@router.get("/history")
async def get_trade_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Get historical trades with pagination."""
    await check_rate_limit(user)
    user_id = str(user["_id"])

    trades, total = await db.get_trades(user_id, page=page, page_size=page_size)

    return {
        "trades": [
            {
                "trade_id": t.get("trade_id", str(t["_id"])),
                "symbol": t.get("symbol"),
                "side": t.get("side"),
                "entry_price": t.get("entry_price"),
                "exit_price": t.get("exit_price"),
                "pnl": t.get("pnl"),
                "pnl_pct": t.get("pnl_pct"),
                "status": t.get("status"),
                "dry_run": t.get("dry_run", True),
                "created_at": t.get("created_at"),
            }
            for t in trades
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
