"""
Pydantic schemas for API request/response validation.
"""
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# --- Enums ---

class Tier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class ChainEnum(str, Enum):
    ETHEREUM = "ethereum"
    ARBITRUM = "arbitrum"


class AnalysisDepth(str, Enum):
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"


class PositionSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


# --- Auth Schemas ---

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    user_id: str


class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    permissions: List[str] = Field(default=["read"])


class APIKeyResponse(BaseModel):
    key_id: str
    api_key: str  # Only returned on creation
    name: str
    permissions: List[str]
    created_at: datetime


class APIKeyInfo(BaseModel):
    key_id: str
    name: str
    permissions: List[str]
    created_at: datetime
    last_used: Optional[datetime] = None


# --- Wallet Schemas ---

class WalletAdd(BaseModel):
    address: str = Field(..., pattern=r"^0x[a-fA-F0-9]{40}$")
    chain: ChainEnum = ChainEnum.ETHEREUM
    label: Optional[str] = None
    alert_threshold_eth: float = Field(default=50.0, ge=0)


class WalletResponse(BaseModel):
    address: str
    chain: str
    label: Optional[str] = None
    alert_threshold_eth: float
    added_at: datetime
    total_signals: int = 0


class WalletListResponse(BaseModel):
    wallets: List[WalletResponse]
    total: int
    limit_for_tier: int


# --- Signal Schemas ---

class SignalResponse(BaseModel):
    id: str
    signal_type: str
    source: str
    strength: str
    confidence: float
    chain: str
    wallet_address: Optional[str] = None
    transaction_hash: Optional[str] = None
    value_eth: Optional[float] = None
    description: str
    reasoning_chain: List[str] = []
    recommended_action: Optional[str] = None
    metadata: Dict[str, Any] = {}
    created_at: datetime


class SignalListResponse(BaseModel):
    signals: List[SignalResponse]
    total: int
    page: int
    page_size: int


class SignalFilter(BaseModel):
    signal_type: Optional[str] = None
    chain: Optional[ChainEnum] = None
    min_confidence: Optional[float] = Field(default=None, ge=0, le=1)
    min_value_eth: Optional[float] = None
    since: Optional[datetime] = None
    wallet_address: Optional[str] = None


# --- Analysis Schemas ---

class WalletAnalysisRequest(BaseModel):
    address: str = Field(..., pattern=r"^0x[a-fA-F0-9]{40}$")
    chain: ChainEnum = ChainEnum.ETHEREUM
    depth: AnalysisDepth = AnalysisDepth.STANDARD


class TransactionAnalysisRequest(BaseModel):
    transaction_hash: str = Field(..., pattern=r"^0x[a-fA-F0-9]{64}$")
    chain: ChainEnum = ChainEnum.ETHEREUM


class AnalysisResponse(BaseModel):
    status: str
    wallet_address: Optional[str] = None
    transaction_hash: Optional[str] = None
    chain: str
    signals: List[SignalResponse] = []
    ai_reasoning: Optional[str] = None
    summary: str
    processing_time_ms: float


# --- Trading Schemas ---

class StrategyInfo(BaseModel):
    name: str
    description: str
    timeframes: List[str]
    min_rr_ratio: float
    win_rate_target: str
    requires_tier: Tier


class StrategyListResponse(BaseModel):
    strategies: List[StrategyInfo]
    enabled_count: int


class TradingSignalResponse(BaseModel):
    id: str
    symbol: str
    signal_type: str  # LONG, SHORT, EXIT_LONG, EXIT_SHORT
    strength: str
    confidence: float
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy_name: str
    reasons: List[str] = []
    created_at: datetime


class BacktestRequest(BaseModel):
    strategy: str
    symbol: str
    timeframe: str = "15m"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    initial_capital: float = 10000.0


class BacktestResponse(BaseModel):
    strategy: str
    symbol: str
    total_trades: int
    win_rate: float
    total_pnl: float
    max_drawdown: float
    sharpe_ratio: Optional[float] = None
    profit_factor: Optional[float] = None


class TradeExecuteRequest(BaseModel):
    symbol: str
    side: PositionSide
    size_pct: float = Field(default=1.0, ge=0.1, le=10.0)
    stop_loss_pct: Optional[float] = Field(default=2.0, ge=0.1, le=20.0)
    take_profit_pct: Optional[float] = Field(default=4.0, ge=0.1, le=50.0)
    dry_run: bool = True


class TradeExecuteResponse(BaseModel):
    trade_id: str
    symbol: str
    side: str
    entry_price: float
    size: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    dry_run: bool
    status: str


# --- Portfolio Schemas ---

class PositionResponse(BaseModel):
    symbol: str
    side: str
    entry_price: float
    current_price: Optional[float] = None
    size: float
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    entry_time: datetime
    status: str


class PortfolioResponse(BaseModel):
    initial_capital: float
    current_capital: float
    total_pnl: float
    total_return_pct: float
    open_positions: List[PositionResponse]
    total_trades: int
    win_rate: float


# --- Market Data Schemas ---

class PriceResponse(BaseModel):
    symbol: str
    price: float
    change_24h: Optional[float] = None
    volume_24h: Optional[float] = None
    timestamp: datetime


class CandleResponse(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


# --- Account & Health ---

class AccountResponse(BaseModel):
    user_id: str
    email: str
    name: Optional[str] = None
    tier: Tier
    wallets_tracked: int
    wallets_limit: int
    signals_today: int
    signals_limit: int
    api_calls_today: int
    api_calls_limit: int
    api_keys: List[APIKeyInfo]
    created_at: datetime


class HealthResponse(BaseModel):
    status: str
    version: str
    services: Dict[str, str]
    uptime_seconds: float


class UsageLimits(BaseModel):
    """Tier-based usage limits."""
    wallets: int
    signals_per_day: int
    api_calls_per_minute: int
    websocket_streams: int
    strategies: int
    data_retention_days: int
    ai_reasoning: bool

    @classmethod
    def for_tier(cls, tier: Tier) -> "UsageLimits":
        limits = {
            Tier.FREE: cls(
                wallets=5, signals_per_day=20, api_calls_per_minute=10,
                websocket_streams=1, strategies=2, data_retention_days=7,
                ai_reasoning=False
            ),
            Tier.PRO: cls(
                wallets=50, signals_per_day=500, api_calls_per_minute=100,
                websocket_streams=5, strategies=16, data_retention_days=90,
                ai_reasoning=True
            ),
            Tier.ENTERPRISE: cls(
                wallets=10000, signals_per_day=100000, api_calls_per_minute=1000,
                websocket_streams=100, strategies=16, data_retention_days=36500,
                ai_reasoning=True
            ),
        }
        return limits[tier]
