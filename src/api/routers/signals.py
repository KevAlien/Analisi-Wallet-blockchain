"""
Signal endpoints: list, filter, detail, and SSE streaming.
"""
import logging
import asyncio
import json
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse

from src.api.auth.security import get_current_user, check_rate_limit
from src.api.models.schemas import (
    SignalResponse, SignalListResponse, Tier, UsageLimits,
)
from src.database import mongodb as db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/signals", tags=["Signals"])


def _signal_to_response(signal: Dict[str, Any]) -> SignalResponse:
    """Convert a MongoDB signal document to API response."""
    return SignalResponse(
        id=str(signal["_id"]),
        signal_type=signal.get("signal_type", "unknown"),
        source=signal.get("source", "unknown"),
        strength=signal.get("strength", "medium"),
        confidence=signal.get("confidence", 0.0),
        chain=signal.get("chain", "ethereum"),
        wallet_address=signal.get("wallet_address"),
        transaction_hash=signal.get("transaction_hash"),
        value_eth=signal.get("value_eth"),
        description=signal.get("description", ""),
        reasoning_chain=signal.get("reasoning_chain", []),
        recommended_action=signal.get("recommended_action"),
        metadata=signal.get("metadata", {}),
        created_at=signal.get("created_at", datetime.utcnow()),
    )


@router.get("", response_model=SignalListResponse)
async def list_signals(
    signal_type: Optional[str] = Query(None),
    chain: Optional[str] = Query(None),
    min_confidence: Optional[float] = Query(None, ge=0, le=1),
    min_value_eth: Optional[float] = Query(None),
    since: Optional[datetime] = Query(None),
    wallet_address: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """
    List signals with optional filtering.

    Accessible by both human users and AI agents via API key.
    """
    await check_rate_limit(user)

    signals, total = await db.get_signals(
        user_id=str(user["_id"]),
        signal_type=signal_type,
        chain=chain,
        min_confidence=min_confidence,
        min_value_eth=min_value_eth,
        since=since,
        wallet_address=wallet_address,
        page=page,
        page_size=page_size,
    )

    return SignalListResponse(
        signals=[_signal_to_response(s) for s in signals],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stream")
async def stream_signals(
    min_confidence: float = Query(0.5, ge=0, le=1),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Server-Sent Events (SSE) stream of real-time signals.

    AI agents and dashboards can subscribe to receive signals in real-time.
    """
    await check_rate_limit(user)
    tier = Tier(user.get("tier", "free"))
    limits = UsageLimits.for_tier(tier)

    if limits.websocket_streams < 1:
        raise HTTPException(
            status_code=403,
            detail="Signal streaming not available on free tier.",
        )

    user_id = str(user["_id"])

    async def event_generator():
        """Generate SSE events from new signals."""
        last_check = datetime.utcnow()

        while True:
            try:
                signals, _ = await db.get_signals(
                    user_id=user_id,
                    min_confidence=min_confidence,
                    since=last_check,
                    page=1,
                    page_size=10,
                )

                for signal in signals:
                    response = _signal_to_response(signal)
                    data = response.model_dump_json()
                    yield f"data: {data}\n\n"

                last_check = datetime.utcnow()
                await asyncio.sleep(5)  # Poll every 5 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"SSE stream error: {e}")
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                await asyncio.sleep(10)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/{signal_id}", response_model=SignalResponse)
async def get_signal(
    signal_id: str, user: Dict[str, Any] = Depends(get_current_user)
):
    """Get detailed information about a specific signal."""
    await check_rate_limit(user)

    signal = await db.get_signal_by_id(signal_id)
    if not signal or str(signal.get("user_id")) != str(user["_id"]):
        raise HTTPException(status_code=404, detail="Signal not found")

    return _signal_to_response(signal)
