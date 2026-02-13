"""
Main FastAPI application - SaaS API for Whale Tracker & Trading Bot.

Serves both human users (via JWT auth) and AI agents (via API keys).
"""
import os
import time
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.database.mongodb import connect_db, close_db
from src.api.routers import auth, wallets, signals, analysis, trading, portfolio, market
from src.api.agent_sdk.tools import router as agent_router
from src.api.websocket_handler import websocket_signal_handler, websocket_price_handler
from src.api.models.schemas import HealthResponse

logger = logging.getLogger(__name__)

# Track startup time for uptime reporting
_start_time = time.time()

VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle events."""
    # Startup
    logger.info("Starting Whale Tracker SaaS API...")
    await connect_db()
    logger.info(f"API v{VERSION} ready")
    yield
    # Shutdown
    logger.info("Shutting down...")
    await close_db()


app = FastAPI(
    title="Whale Tracker & Trading Bot API",
    description=(
        "Multi-tenant SaaS platform for blockchain whale tracking, "
        "automated trading, and AI-powered signal generation. "
        "Designed for both human users and AI agents.\n\n"
        "## Authentication\n"
        "- **Human users**: `POST /api/v1/auth/login` for JWT tokens\n"
        "- **AI agents**: Use `X-API-Key` header with API keys from "
        "`POST /api/v1/auth/api-keys`\n\n"
        "## Agent SDK\n"
        "AI agents can discover tools via `GET /api/v1/agent/tools` "
        "and invoke them via `POST /api/v1/agent/invoke`.\n\n"
        "## WebSocket\n"
        "Real-time signals: `ws://host/api/v1/ws/signals?api_key=...`\n"
        "Real-time prices: `ws://host/api/v1/ws/prices?api_key=...`"
    ),
    version=VERSION,
    lifespan=lifespan,
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
)

# CORS middleware (configure for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = (time.time() - start) * 1000

    logger.info(
        f"{request.method} {request.url.path} "
        f"-> {response.status_code} ({elapsed:.1f}ms)"
    )
    return response


# --- Register Routers ---
API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(wallets.router, prefix=API_PREFIX)
app.include_router(signals.router, prefix=API_PREFIX)
app.include_router(analysis.router, prefix=API_PREFIX)
app.include_router(trading.router, prefix=API_PREFIX)
app.include_router(portfolio.router, prefix=API_PREFIX)
app.include_router(market.router, prefix=API_PREFIX)
app.include_router(agent_router, prefix=API_PREFIX)


# --- WebSocket Endpoints ---

@app.websocket("/api/v1/ws/signals")
async def ws_signals(websocket):
    await websocket_signal_handler(websocket)


@app.websocket("/api/v1/ws/prices")
async def ws_prices(websocket):
    await websocket_price_handler(websocket)


# --- Health Check ---

@app.get("/api/v1/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    System health check. No authentication required.

    Returns service status and uptime.
    """
    uptime = time.time() - _start_time

    # Check service connectivity
    services = {"api": "healthy"}

    try:
        from src.database.mongodb import get_db
        db = await get_db()
        await db.command("ping")
        services["mongodb"] = "healthy"
    except Exception:
        services["mongodb"] = "unhealthy"

    return HealthResponse(
        status="healthy" if all(v == "healthy" for v in services.values()) else "degraded",
        version=VERSION,
        services=services,
        uptime_seconds=round(uptime, 2),
    )


# --- Account Info ---

@app.get("/api/v1/account", tags=["Account"])
async def get_account_info(request: Request):
    """
    Get current account information, usage stats, and limits.
    Requires authentication.
    """
    from src.api.auth.security import get_current_user
    from src.api.models.schemas import Tier, UsageLimits, AccountResponse, APIKeyInfo
    from src.database import mongodb as db

    user = await get_current_user(
        credentials=None,
        api_key=request.headers.get("X-API-Key"),
    )

    # If no API key, try bearer
    if not user:
        from fastapi.security import HTTPAuthorizationCredentials
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
            user = await get_current_user(credentials=creds)

    tier = Tier(user.get("tier", "free"))
    limits = UsageLimits.for_tier(tier)
    wallet_count = await db.count_tracked_wallets(str(user["_id"]))
    usage = user.get("usage", {})

    api_keys = [
        APIKeyInfo(
            key_id=k["key_id"],
            name=k["name"],
            permissions=k["permissions"],
            created_at=k["created_at"],
            last_used=k.get("last_used"),
        )
        for k in user.get("api_keys", [])
    ]

    return AccountResponse(
        user_id=str(user["_id"]),
        email=user["email"],
        name=user.get("name"),
        tier=tier,
        wallets_tracked=wallet_count,
        wallets_limit=limits.wallets,
        signals_today=usage.get("signals_today", 0),
        signals_limit=limits.signals_per_day,
        api_calls_today=usage.get("api_calls_today", 0),
        api_calls_limit=limits.api_calls_per_minute * 60 * 24,
        api_keys=api_keys,
        created_at=user.get("created_at", datetime.utcnow()),
    )


# --- Root redirect ---

@app.get("/", include_in_schema=False)
async def root():
    return {
        "name": "Whale Tracker & Trading Bot SaaS API",
        "version": VERSION,
        "docs": "/api/v1/docs",
        "health": "/api/v1/health",
        "agent_tools": "/api/v1/agent/tools",
    }
