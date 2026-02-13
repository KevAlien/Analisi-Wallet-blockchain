"""
On-demand analysis endpoints: wallet analysis, transaction analysis.
"""
import time
import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends

from src.api.auth.security import get_current_user, check_rate_limit, check_tier_permission
from src.api.models.schemas import (
    WalletAnalysisRequest, TransactionAnalysisRequest, AnalysisResponse,
    SignalResponse, Tier, AnalysisDepth,
)
from src.analysis.transaction_analyzer import TransactionAnalyzer
from src.signals.signal_generator import SignalGenerator
from src.fetching.explorer_api import ExplorerAPIClient
from src.database import mongodb as db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analysis", tags=["Analysis"])

# Shared instances (will be initialized on first use)
_analyzer = None
_signal_gen = None
_explorer = None


def _get_analyzer():
    global _analyzer
    if _analyzer is None:
        _analyzer = TransactionAnalyzer()
    return _analyzer


def _get_signal_generator():
    global _signal_gen
    if _signal_gen is None:
        _signal_gen = SignalGenerator()
    return _signal_gen


def _get_explorer():
    global _explorer
    if _explorer is None:
        _explorer = ExplorerAPIClient()
    return _explorer


@router.post("/wallet", response_model=AnalysisResponse)
async def analyze_wallet(
    body: WalletAnalysisRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Analyze a wallet on-demand for whale activity.

    - **quick**: Last 10 transactions, rule-based only
    - **standard**: Last 50 transactions, with pattern detection
    - **deep**: Full history scan + AI reasoning (Pro+ tier)
    """
    await check_rate_limit(user)

    if body.depth == AnalysisDepth.DEEP:
        await check_tier_permission(user, Tier.PRO)

    start_time = time.time()
    user_id = str(user["_id"])

    try:
        explorer = _get_explorer()
        analyzer = _get_analyzer()
        signal_gen = _get_signal_generator()

        # Determine analysis scope
        tx_limit = {
            AnalysisDepth.QUICK: 10,
            AnalysisDepth.STANDARD: 50,
            AnalysisDepth.DEEP: 200,
        }[body.depth]

        # Fetch transactions via explorer API
        from src.config.wallet_registry import Chain
        chain = Chain.ETHEREUM if body.chain.value == "ethereum" else Chain.ARBITRUM

        transactions = explorer.get_wallet_transactions(
            address=body.address,
            chain=chain,
            start_block=0,
            end_block=99999999,
        )[:tx_limit]

        # Analyze each transaction
        signals = []
        for tx in transactions:
            tx["chain"] = body.chain.value
            analyzed = analyzer.analyze_transaction(tx)

            if analyzed.get("is_significant"):
                generated = signal_gen.generate_signals(analyzed)
                for sig in generated:
                    signal_data = sig.to_dict()
                    signal_id = await db.store_signal(user_id, signal_data)
                    signal_data["_id"] = signal_id
                    signal_data["id"] = signal_id

                    signals.append(SignalResponse(
                        id=signal_id,
                        signal_type=signal_data.get("signal_type", "unknown"),
                        source="on_demand_analysis",
                        strength=signal_data.get("strength", "medium"),
                        confidence=signal_data.get("confidence", 0.0),
                        chain=body.chain.value,
                        wallet_address=body.address,
                        transaction_hash=signal_data.get("transaction_hash"),
                        value_eth=signal_data.get("value_eth"),
                        description=signal_data.get("description", ""),
                        reasoning_chain=signal_data.get("reasoning_chain", []),
                        recommended_action=signal_data.get("recommended_action"),
                        metadata={},
                        created_at=datetime.utcnow(),
                    ))

        await db.increment_usage(user_id, "signals_today", len(signals))

        elapsed_ms = (time.time() - start_time) * 1000

        return AnalysisResponse(
            status="completed",
            wallet_address=body.address,
            chain=body.chain.value,
            signals=signals,
            summary=f"Analyzed {len(transactions)} transactions, found {len(signals)} signals",
            processing_time_ms=round(elapsed_ms, 2),
        )

    except Exception as e:
        logger.error(f"Wallet analysis failed: {e}")
        elapsed_ms = (time.time() - start_time) * 1000
        return AnalysisResponse(
            status="error",
            wallet_address=body.address,
            chain=body.chain.value,
            summary=f"Analysis failed: {str(e)}",
            processing_time_ms=round(elapsed_ms, 2),
        )


@router.post("/transaction", response_model=AnalysisResponse)
async def analyze_transaction(
    body: TransactionAnalysisRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Analyze a specific transaction for significance and signals."""
    await check_rate_limit(user)

    start_time = time.time()
    user_id = str(user["_id"])

    try:
        analyzer = _get_analyzer()
        signal_gen = _get_signal_generator()

        # Build a minimal transaction dict for analysis
        tx_data = {
            "hash": body.transaction_hash,
            "chain": body.chain.value,
        }

        analyzed = analyzer.analyze_transaction(tx_data)

        signals = []
        if analyzed.get("is_significant"):
            generated = signal_gen.generate_signals(analyzed)
            for sig in generated:
                signal_data = sig.to_dict()
                signal_id = await db.store_signal(user_id, signal_data)

                signals.append(SignalResponse(
                    id=signal_id,
                    signal_type=signal_data.get("signal_type", "unknown"),
                    source="on_demand_analysis",
                    strength=signal_data.get("strength", "medium"),
                    confidence=signal_data.get("confidence", 0.0),
                    chain=body.chain.value,
                    transaction_hash=body.transaction_hash,
                    value_eth=signal_data.get("value_eth"),
                    description=signal_data.get("description", ""),
                    reasoning_chain=[],
                    metadata={},
                    created_at=datetime.utcnow(),
                ))

        elapsed_ms = (time.time() - start_time) * 1000

        return AnalysisResponse(
            status="completed",
            transaction_hash=body.transaction_hash,
            chain=body.chain.value,
            signals=signals,
            summary=f"Transaction analysis complete. Signals: {len(signals)}",
            processing_time_ms=round(elapsed_ms, 2),
        )

    except Exception as e:
        logger.error(f"Transaction analysis failed: {e}")
        elapsed_ms = (time.time() - start_time) * 1000
        return AnalysisResponse(
            status="error",
            transaction_hash=body.transaction_hash,
            chain=body.chain.value,
            summary=f"Analysis failed: {str(e)}",
            processing_time_ms=round(elapsed_ms, 2),
        )
