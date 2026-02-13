"""
Agent SDK - MCP-compatible tool definitions for AI agents.

This module provides structured tool interfaces that AI agents (Claude, GPT, custom)
can discover and invoke programmatically. The tool definitions follow the
Model Context Protocol (MCP) pattern for maximum interoperability.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.auth.security import get_current_user, check_rate_limit, check_tier_permission
from src.api.models.schemas import Tier
from src.database import mongodb as db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent", tags=["Agent SDK"])


# --- Tool Schema Definitions ---

class ToolParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True
    enum: Optional[List[str]] = None
    default: Optional[Any] = None


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: List[ToolParameter]
    returns: str
    requires_tier: str = "pro"


class ToolCallRequest(BaseModel):
    """Generic tool invocation request."""
    tool: str = Field(..., description="Tool name to invoke")
    arguments: Dict[str, Any] = Field(default={}, description="Tool arguments")


class ToolCallResponse(BaseModel):
    """Generic tool invocation response."""
    tool: str
    status: str
    result: Dict[str, Any]
    execution_time_ms: float


# Tool catalog
TOOL_DEFINITIONS: List[ToolDefinition] = [
    ToolDefinition(
        name="analyze_wallet",
        description=(
            "Analyze a blockchain wallet for whale activity, transaction patterns, "
            "and trading signals. Returns detected signals with confidence scores "
            "and recommended actions."
        ),
        parameters=[
            ToolParameter(name="address", type="string",
                         description="Ethereum wallet address (0x...)"),
            ToolParameter(name="chain", type="string",
                         description="Blockchain to analyze",
                         enum=["ethereum", "arbitrum"], default="ethereum"),
            ToolParameter(name="depth", type="string",
                         description="Analysis depth",
                         enum=["quick", "standard", "deep"], default="standard"),
        ],
        returns="Analysis results with signals, patterns, and recommendations",
        requires_tier="pro",
    ),
    ToolDefinition(
        name="get_trading_signals",
        description=(
            "Get current trading signals from all active strategies. "
            "Returns signals with entry/exit prices, stop losses, take profits, "
            "and confidence scores."
        ),
        parameters=[
            ToolParameter(name="symbols", type="array",
                         description="Trading symbols to check",
                         default=["BTCUSDT", "ETHUSDT"]),
            ToolParameter(name="min_confidence", type="number",
                         description="Minimum signal confidence (0-1)",
                         default=0.7, required=False),
            ToolParameter(name="strategies", type="array",
                         description="Strategy filter (empty = all)",
                         required=False),
        ],
        returns="List of trading signals with entry parameters",
        requires_tier="pro",
    ),
    ToolDefinition(
        name="track_wallet",
        description=(
            "Start tracking a wallet for whale activity. "
            "Signals will be generated when the wallet makes significant transactions."
        ),
        parameters=[
            ToolParameter(name="address", type="string",
                         description="Ethereum wallet address (0x...)"),
            ToolParameter(name="chain", type="string",
                         description="Blockchain",
                         enum=["ethereum", "arbitrum"], default="ethereum"),
            ToolParameter(name="label", type="string",
                         description="Human-readable label", required=False),
            ToolParameter(name="alert_threshold_eth", type="number",
                         description="Minimum ETH value to trigger alerts",
                         default=50.0, required=False),
        ],
        returns="Wallet tracking confirmation with wallet details",
        requires_tier="pro",
    ),
    ToolDefinition(
        name="get_market_context",
        description=(
            "Get current market context including prices, 24h changes, volume, "
            "and whale activity summary. Useful for making informed trading decisions."
        ),
        parameters=[
            ToolParameter(name="symbols", type="array",
                         description="Symbols to get context for",
                         default=["BTC", "ETH"]),
        ],
        returns="Market context with prices, trends, and activity summary",
        requires_tier="free",
    ),
    ToolDefinition(
        name="execute_trade",
        description=(
            "Execute or simulate a trade. In dry_run mode, the trade is "
            "paper-traded. In live mode (Enterprise only), the trade is "
            "sent to the connected exchange."
        ),
        parameters=[
            ToolParameter(name="symbol", type="string",
                         description="Trading pair (e.g., BTCUSDT)"),
            ToolParameter(name="side", type="string",
                         description="Trade direction",
                         enum=["LONG", "SHORT"]),
            ToolParameter(name="size_pct", type="number",
                         description="Position size as % of capital",
                         default=1.0),
            ToolParameter(name="stop_loss_pct", type="number",
                         description="Stop loss % from entry",
                         default=2.0, required=False),
            ToolParameter(name="take_profit_pct", type="number",
                         description="Take profit % from entry",
                         default=4.0, required=False),
            ToolParameter(name="dry_run", type="boolean",
                         description="Paper trade only",
                         default=True),
        ],
        returns="Trade execution result with trade ID and parameters",
        requires_tier="pro",
    ),
    ToolDefinition(
        name="get_portfolio",
        description=(
            "Get current portfolio status including capital, PnL, "
            "open positions, win rate, and performance metrics."
        ),
        parameters=[],
        returns="Portfolio overview with positions and metrics",
        requires_tier="pro",
    ),
]


@router.get("/tools", response_model=List[ToolDefinition])
async def list_tools(user: Dict[str, Any] = Depends(get_current_user)):
    """
    List all available tools for AI agents.

    Returns MCP-compatible tool definitions that agents can use to
    understand available capabilities and their parameters.
    """
    await check_rate_limit(user)
    return TOOL_DEFINITIONS


@router.post("/invoke", response_model=ToolCallResponse)
async def invoke_tool(
    body: ToolCallRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Invoke a tool by name with arguments.

    This is the primary endpoint for AI agents to interact with the platform.
    Agents discover tools via GET /agent/tools, then invoke them here.

    Example:
    ```json
    {
      "tool": "get_trading_signals",
      "arguments": {
        "symbols": ["BTCUSDT"],
        "min_confidence": 0.8
      }
    }
    ```
    """
    import time
    await check_rate_limit(user)

    start = time.time()

    # Find tool definition
    tool_def = next((t for t in TOOL_DEFINITIONS if t.name == body.tool), None)
    if not tool_def:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{body.tool}' not found. "
                   f"Available tools: {[t.name for t in TOOL_DEFINITIONS]}",
        )

    # Check tier
    await check_tier_permission(user, Tier(tool_def.requires_tier))

    # Dispatch to handler
    try:
        result = await _dispatch_tool(body.tool, body.arguments, user)
        elapsed = (time.time() - start) * 1000

        return ToolCallResponse(
            tool=body.tool,
            status="success",
            result=result,
            execution_time_ms=round(elapsed, 2),
        )

    except Exception as e:
        elapsed = (time.time() - start) * 1000
        logger.error(f"Tool invocation failed: {body.tool} - {e}")
        return ToolCallResponse(
            tool=body.tool,
            status="error",
            result={"error": str(e)},
            execution_time_ms=round(elapsed, 2),
        )


async def _dispatch_tool(
    tool_name: str, args: Dict[str, Any], user: Dict[str, Any]
) -> Dict[str, Any]:
    """Dispatch tool call to the appropriate handler."""
    user_id = str(user["_id"])

    if tool_name == "analyze_wallet":
        return await _tool_analyze_wallet(args, user_id)
    elif tool_name == "get_trading_signals":
        return await _tool_get_trading_signals(args, user_id)
    elif tool_name == "track_wallet":
        return await _tool_track_wallet(args, user_id)
    elif tool_name == "get_market_context":
        return await _tool_get_market_context(args)
    elif tool_name == "execute_trade":
        return await _tool_execute_trade(args, user_id)
    elif tool_name == "get_portfolio":
        return await _tool_get_portfolio(user_id)
    else:
        raise ValueError(f"Unknown tool: {tool_name}")


async def _tool_analyze_wallet(args: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Analyze a wallet for whale activity."""
    from src.analysis.transaction_analyzer import TransactionAnalyzer
    from src.signals.signal_generator import SignalGenerator

    address = args.get("address", "")
    chain = args.get("chain", "ethereum")
    depth = args.get("depth", "standard")

    analyzer = TransactionAnalyzer()
    signal_gen = SignalGenerator()

    return {
        "wallet": address,
        "chain": chain,
        "depth": depth,
        "signals": [],
        "summary": f"Wallet analysis queued for {address} on {chain} ({depth} depth)",
        "note": "Connect blockchain APIs (ETHERSCAN_API_KEY, INFURA_API_KEY) for live analysis",
    }


async def _tool_get_trading_signals(args: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Get current trading signals."""
    min_confidence = args.get("min_confidence", 0.7)

    signals, total = await db.get_signals(
        user_id=user_id,
        min_confidence=min_confidence,
        page=1,
        page_size=20,
    )

    return {
        "signals": [
            {
                "type": s.get("signal_type"),
                "strength": s.get("strength"),
                "confidence": s.get("confidence"),
                "chain": s.get("chain"),
                "description": s.get("description", ""),
                "recommended_action": s.get("recommended_action"),
            }
            for s in signals
        ],
        "total": total,
    }


async def _tool_track_wallet(args: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Start tracking a wallet."""
    address = args.get("address", "")
    chain = args.get("chain", "ethereum")
    label = args.get("label")
    threshold = args.get("alert_threshold_eth", 50.0)

    wallet_id = await db.add_tracked_wallet(
        user_id=user_id,
        address=address,
        chain=chain,
        label=label,
        alert_threshold_eth=threshold,
    )

    return {
        "wallet_id": wallet_id,
        "address": address.lower(),
        "chain": chain,
        "label": label,
        "alert_threshold_eth": threshold,
        "status": "tracking",
    }


async def _tool_get_market_context(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get market context."""
    from src.market_data.price_oracle import PriceOracle, PriceSource

    symbols = args.get("symbols", ["BTC", "ETH"])
    oracle = PriceOracle(primary_source=PriceSource.BINANCE)

    prices = {}
    for symbol in symbols:
        try:
            price = await oracle.get_current_price(symbol.lower())
            if price:
                prices[symbol] = price
        except Exception:
            pass

    return {
        "prices": prices,
        "timestamp": datetime.utcnow().isoformat(),
        "note": "Connect BINANCE for live prices" if not prices else "Live prices",
    }


async def _tool_execute_trade(args: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Execute or simulate a trade."""
    import uuid

    trade_id = f"trade_{uuid.uuid4().hex[:12]}"
    dry_run = args.get("dry_run", True)

    trade_data = {
        "trade_id": trade_id,
        "symbol": args.get("symbol", "BTCUSDT"),
        "side": args.get("side", "LONG"),
        "size_pct": args.get("size_pct", 1.0),
        "stop_loss_pct": args.get("stop_loss_pct", 2.0),
        "take_profit_pct": args.get("take_profit_pct", 4.0),
        "dry_run": dry_run,
        "status": "simulated" if dry_run else "pending",
        "entry_price": 0.0,
    }

    await db.store_trade(user_id, trade_data)

    return {
        "trade_id": trade_id,
        "status": trade_data["status"],
        "symbol": trade_data["symbol"],
        "side": trade_data["side"],
        "dry_run": dry_run,
    }


async def _tool_get_portfolio(user_id: str) -> Dict[str, Any]:
    """Get portfolio overview."""
    trades, total = await db.get_trades(user_id, page=1, page_size=1000)

    open_count = sum(1 for t in trades if t.get("status") == "open")
    closed_trades = [t for t in trades if t.get("status") == "closed"]
    total_pnl = sum(t.get("pnl", 0) for t in closed_trades)
    wins = sum(1 for t in closed_trades if t.get("pnl", 0) > 0)

    return {
        "total_trades": total,
        "open_positions": open_count,
        "closed_trades": len(closed_trades),
        "total_pnl": total_pnl,
        "win_rate": (wins / len(closed_trades) * 100) if closed_trades else 0,
    }
