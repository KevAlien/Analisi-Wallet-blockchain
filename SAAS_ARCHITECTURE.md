# SaaS Platform Architecture - Whale Tracker & Trading Bot

## Vision

Transform the current CLI-based whale tracking and trading bot into a **multi-tenant SaaS platform** accessible by both **human users** (via Web Dashboard + API) and **AI agents** (via REST API + WebSocket + MCP-compatible tool interface).

## Architecture Overview

```
                    +------------------+
                    |   Web Dashboard  |  (Human Users)
                    |   (Future: React)|
                    +--------+---------+
                             |
                    +--------v---------+
                    |   API Gateway    |  FastAPI + WebSocket
                    |   /api/v1/...    |
                    +--------+---------+
                             |
              +--------------+---------------+
              |              |               |
     +--------v---+  +------v-----+  +------v------+
     |   Auth     |  |  Rate      |  |  Billing    |
     |   JWT +    |  |  Limiter   |  |  Tiers      |
     |   API Keys |  |  (Redis)   |  |  (Stripe)   |
     +--------+---+  +------+-----+  +------+------+
              |              |               |
     +--------v--------------v---------------v------+
     |              Core Services                    |
     |  +----------+  +-----------+  +-----------+  |
     |  | Whale    |  | Trading   |  | AI        |  |
     |  | Tracker  |  | Engine    |  | Reasoning |  |
     |  +----------+  +-----------+  +-----------+  |
     |  +----------+  +-----------+  +-----------+  |
     |  | Signal   |  | Portfolio |  | Market    |  |
     |  | Pipeline |  | Manager   |  | Data      |  |
     |  +----------+  +-----------+  +-----------+  |
     +-------------------+--+-----------------------+
                         |  |
              +----------v--v-----------+
              |     Persistence         |
              |  MongoDB  |  Redis      |
              +----------------------------+
```

## API Design (Human + Agent)

### Authentication
- **Human users**: JWT tokens (login/register) + session management
- **AI Agents**: API keys with scoped permissions (read-only, trade, admin)
- **Rate limiting**: Per-tier, per-endpoint, Redis-backed

### Subscription Tiers

| Feature              | Free       | Pro ($29/mo) | Enterprise ($99/mo) |
|---------------------|------------|--------------|---------------------|
| Wallets tracked     | 5          | 50           | Unlimited           |
| Signals/day         | 20         | 500          | Unlimited           |
| Trading strategies  | 2          | All 16       | All + Custom        |
| AI reasoning        | -          | Basic        | Full (Claude/GPT)   |
| API calls/min       | 10         | 100          | 1000                |
| WebSocket streams   | 1          | 5            | Unlimited           |
| Data retention      | 7 days     | 90 days      | Unlimited           |
| Agent SDK access    | -          | Full         | Full + Priority     |

### REST API Endpoints

```
POST   /api/v1/auth/register          # Create account
POST   /api/v1/auth/login             # Get JWT token
POST   /api/v1/auth/api-keys          # Generate API key
DELETE /api/v1/auth/api-keys/{key_id} # Revoke API key

GET    /api/v1/wallets                # List tracked wallets
POST   /api/v1/wallets                # Add wallet to track
DELETE /api/v1/wallets/{address}      # Remove wallet

GET    /api/v1/signals                # Get signals (with filters)
GET    /api/v1/signals/stream         # SSE stream of real-time signals
GET    /api/v1/signals/{id}           # Get signal details

POST   /api/v1/analysis/wallet        # Analyze a wallet on-demand
POST   /api/v1/analysis/transaction   # Analyze a specific transaction

GET    /api/v1/trading/strategies     # List available strategies
POST   /api/v1/trading/backtest       # Run backtest on strategy
GET    /api/v1/trading/signals        # Get trading signals
POST   /api/v1/trading/execute        # Execute a trade (dry-run or live)

GET    /api/v1/portfolio              # Get portfolio overview
GET    /api/v1/portfolio/positions    # Get open positions
GET    /api/v1/portfolio/history      # Get trade history

GET    /api/v1/market/prices          # Get current prices
GET    /api/v1/market/candles         # Get OHLCV candles

WS     /api/v1/ws/signals             # WebSocket for real-time signals
WS     /api/v1/ws/prices              # WebSocket for price updates

GET    /api/v1/health                 # Health check
GET    /api/v1/account                # Account info + usage stats
```

### Agent SDK Interface (MCP-Compatible)

AI agents can interact via structured tool definitions:

```json
{
  "tools": [
    {
      "name": "analyze_wallet",
      "description": "Analyze a blockchain wallet for whale activity, transaction patterns, and trading signals",
      "parameters": {
        "address": "0x...",
        "chain": "ethereum|arbitrum",
        "depth": "quick|standard|deep"
      }
    },
    {
      "name": "get_trading_signals",
      "description": "Get current trading signals from all active strategies",
      "parameters": {
        "symbols": ["BTCUSDT", "ETHUSDT"],
        "min_confidence": 0.7
      }
    },
    {
      "name": "track_wallet",
      "description": "Start tracking a wallet for whale activity",
      "parameters": {
        "address": "0x...",
        "chain": "ethereum",
        "alert_threshold_eth": 50
      }
    },
    {
      "name": "get_market_context",
      "description": "Get current market context including prices, trends, and sentiment",
      "parameters": {
        "symbols": ["BTC", "ETH"]
      }
    },
    {
      "name": "execute_trade",
      "description": "Execute or simulate a trade based on signals",
      "parameters": {
        "symbol": "BTCUSDT",
        "side": "LONG|SHORT",
        "size_pct": 1.0,
        "dry_run": true
      }
    }
  ]
}
```

## Data Model

### Users Collection (MongoDB)
```json
{
  "_id": "ObjectId",
  "email": "user@example.com",
  "password_hash": "bcrypt...",
  "tier": "free|pro|enterprise",
  "api_keys": [
    {
      "key_id": "wt_...",
      "key_hash": "sha256...",
      "name": "My Bot",
      "permissions": ["read", "trade"],
      "created_at": "2025-01-01T00:00:00Z",
      "last_used": "2025-01-15T12:00:00Z"
    }
  ],
  "tracked_wallets": ["0x..."],
  "settings": {
    "default_chain": "ethereum",
    "notification_channels": ["telegram", "webhook"],
    "risk_per_trade_pct": 1.0
  },
  "usage": {
    "signals_today": 15,
    "api_calls_today": 42,
    "last_reset": "2025-01-15T00:00:00Z"
  },
  "created_at": "2025-01-01T00:00:00Z"
}
```

### Signals Collection (MongoDB)
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "signal_type": "accumulation|distribution|...",
  "source": "whale_tracker|trading_bot|ai_reasoning",
  "strength": "low|medium|high|very_high",
  "confidence": 0.85,
  "chain": "ethereum",
  "wallet_address": "0x...",
  "transaction_hash": "0x...",
  "value_eth": 500.0,
  "reasoning_chain": ["step1", "step2"],
  "recommended_action": "LONG|SHORT|NEUTRAL",
  "metadata": {},
  "created_at": "2025-01-15T12:00:00Z",
  "expires_at": "2025-01-22T12:00:00Z"
}
```

## Deployment

### Docker Compose Stack
- **api**: FastAPI application (port 8000)
- **worker**: Background whale tracker + trading bot
- **mongodb**: Data persistence
- **redis**: Caching, rate limiting, pub/sub
- **ollama**: Local LLM (optional)

### Environment
All configuration via environment variables, supporting 12-factor app principles.
