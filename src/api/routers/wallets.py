"""
Wallet tracking endpoints.
"""
import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends

from src.api.auth.security import get_current_user, check_rate_limit
from src.api.models.schemas import (
    WalletAdd, WalletResponse, WalletListResponse, Tier, UsageLimits,
)
from src.database import mongodb as db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/wallets", tags=["Wallet Tracking"])


@router.get("", response_model=WalletListResponse)
async def list_wallets(user: Dict[str, Any] = Depends(get_current_user)):
    """List all tracked wallets for the current user."""
    await check_rate_limit(user)

    wallets = await db.get_tracked_wallets(str(user["_id"]))
    tier = Tier(user.get("tier", "free"))
    limits = UsageLimits.for_tier(tier)

    wallet_responses = [
        WalletResponse(
            address=w["address"],
            chain=w["chain"],
            label=w.get("label"),
            alert_threshold_eth=w.get("alert_threshold_eth", 50.0),
            added_at=w.get("added_at", datetime.utcnow()),
            total_signals=w.get("total_signals", 0),
        )
        for w in wallets
    ]

    return WalletListResponse(
        wallets=wallet_responses,
        total=len(wallet_responses),
        limit_for_tier=limits.wallets,
    )


@router.post("", response_model=WalletResponse, status_code=201)
async def add_wallet(body: WalletAdd, user: Dict[str, Any] = Depends(get_current_user)):
    """Add a wallet to track."""
    await check_rate_limit(user)

    user_id = str(user["_id"])
    tier = Tier(user.get("tier", "free"))
    limits = UsageLimits.for_tier(tier)

    # Check wallet limit
    current_count = await db.count_tracked_wallets(user_id)
    if current_count >= limits.wallets:
        raise HTTPException(
            status_code=403,
            detail=f"Wallet limit reached ({limits.wallets}) for {tier.value} tier. "
                   f"Upgrade to track more wallets.",
        )

    # Check for duplicate
    existing = await db.get_tracked_wallets(user_id)
    for w in existing:
        if w["address"] == body.address.lower() and w["chain"] == body.chain.value:
            raise HTTPException(status_code=409, detail="Wallet already tracked")

    await db.add_tracked_wallet(
        user_id=user_id,
        address=body.address,
        chain=body.chain.value,
        label=body.label,
        alert_threshold_eth=body.alert_threshold_eth,
    )

    logger.info(f"Wallet tracked: {body.address} on {body.chain.value} by {user['email']}")

    return WalletResponse(
        address=body.address.lower(),
        chain=body.chain.value,
        label=body.label,
        alert_threshold_eth=body.alert_threshold_eth,
        added_at=datetime.utcnow(),
        total_signals=0,
    )


@router.delete("/{address}")
async def remove_wallet(address: str, user: Dict[str, Any] = Depends(get_current_user)):
    """Remove a tracked wallet."""
    await check_rate_limit(user)

    await db.remove_tracked_wallet(str(user["_id"]), address)
    return {"status": "removed", "address": address.lower()}
