# SentryCage — Walk-Through Guide

**What it is:** A self-hosted whale wallet tracker for Ethereum and 60+ EVM chains. It monitors large on-chain transactions, runs AI analysis locally, and sends real-time alerts to your Telegram.

---

## What's live today

Everything in this guide works right now:

- [x] Whale tracking on Ethereum + 60+ EVM chains
- [x] Six on-chain signals: accumulation, distribution, CEX deposit/withdrawal, large transfer, unusual activity
- [x] AI reasoning with live market context (Ollama local / Claude / OpenAI)
- [x] Telegram alerts, local SQLite storage
- [x] 75/75 automated tests passing

Next on the roadmap: Smart Money Following, sharper price-aware scoring, and backtesting.

The 75 tests check the software, not your hardware. If a run struggles because the
machine is short on RAM, offline, or rate-limited, SentryCage degrades on purpose
rather than crashing — see [Part 8 — Troubleshooting](#part-8--troubleshooting).

---

## Part 1 — Prerequisites

Before you start, gather these four things:

| What | How to get it |
|---|---|
| **Etherscan V2 API key** | Register at etherscan.io/apis → create a key (free tier is fine) |
| **Telegram bot token** | Open Telegram → message @BotFather → `/newbot` → copy the token |
| **Your Telegram chat ID** | Message @userinfobot → it replies with your numeric ID |
| **Docker + Docker Compose** | Install Docker Desktop (Windows/Mac) or Docker Engine (Linux) |

Optional for AI reasoning (otherwise falls back to rule-based mode):
- **Ollama** with `llama3.1:8b` pulled — or a Claude / OpenAI API key

---

## Part 2 — Installation

### Option A: Docker (recommended — works on Windows, macOS, Linux)

```bash
# 1. Clone the repo
git clone https://github.com/SentryCage/sentrycage.git
cd sentrycage

# 2. Copy the config template
cp .env.example .env
```

Open `.env` in any text editor and fill in the three required fields at minimum:

```env
ETHERSCAN_API_KEY=your_key_here
TELEGRAM_BOT_TOKEN=123456789:ABCdef...
TELEGRAM_CHAT_ID=987654321
```

Then start everything:

```bash
docker compose up -d
```

Docker will build the image, start the tracker and the Ollama LLM container, and pull the model (~5 GB) on first run. This takes a few minutes on the first boot.

---

### Option B: Manual (Python, no Docker)

Requires **Python 3.9+** (tested on 3.12).

```bash
git clone https://github.com/SentryCage/sentrycage.git
cd sentrycage

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# edit .env with your keys

python main.py
```

---

### Option C: Android (Termux)

```bash
pkg update && pkg upgrade
pkg install python git

git clone https://github.com/SentryCage/sentrycage.git
cd sentrycage

pip install -r requirements.txt

cp .env.example .env
nano .env     # fill in your keys

python main.py
```

> Ollama is not available on Android. AI reasoning falls back to rule-based mode automatically — no action needed.

---

## Part 3 — Verifying the Startup

Watch the logs to confirm everything is working:

```bash
docker compose logs -f sentrycage
```

A healthy startup looks like:

```
INFO  Database initialized: data/whale_tracker.db
INFO  Trial Pro started — 14 days of full access
INFO  TelegramNotifier connected as @YourBot
INFO  SentryCage is running
```

Within 1–2 minutes you should receive a startup message directly on Telegram. If you don't, see the troubleshooting section below.

Check the current tier and trial status at any time:

```bash
docker exec sentrycage python -m src.config status
```

---

## Part 4 — Configuration

### AI Reasoning Provider

Edit `.env` to choose your LLM backend:

| Provider | Setting | Cost | Notes |
|---|---|---|---|
| **Ollama** (default) | `LLM_PROVIDER=ollama` | Free | Needs 8–16 GB RAM |
| **LMStudio** | `LLM_PROVIDER=lmstudio` | Free | GUI app on your host |
| **Claude API** | `LLM_PROVIDER=claude` | ~€3/day | Best quality |
| **OpenAI** | `LLM_PROVIDER=openai` | ~€2–5/day | Good quality |

To disable AI reasoning entirely and run rule-based only:

```env
ENABLE_REASONING=false
```

### Polling and Thresholds

```env
POLLING_INTERVAL=60          # seconds between blockchain scans
TRANSACTION_THRESHOLD=50     # minimum ETH value to trigger an alert
```

### Key Tuning Parameters

```env
MAX_REASONING_ITERATIONS=5   # how many AI refinement passes per signal
REASONING_TIMEOUT=30         # seconds before AI times out (falls back to rule-based)
```

---

## Part 5 — Adding Wallets to Track

Edit `src/config/wallet_registry.py`:

```python
ALL_WALLETS = [
    WalletInfo(
        address="0x28c6c06298d514db089934071355e5743bf21d60",
        label="Binance Hot Wallet",
        chains=[Chain.ETHEREUM],
        alert_threshold_eth=50.0,
    ),
    WalletInfo(
        address="0xYourWalletHere",
        label="My whale",
        chains=[Chain.ETHEREUM, Chain.ARBITRUM],  # Pro required for Arbitrum
        alert_threshold_eth=10.0,
    ),
]
```

After saving, restart the tracker:

```bash
docker compose restart sentrycage
```

> The file is mounted read-only into the container, so edits on your host take effect on the next restart without rebuilding.

---

## Part 6 — Understanding Telegram Alerts

A typical alert looks like:

```
🔴 DISTRIBUTION — HIGH CONFIDENCE
Wallet: 0x28c6...1d60 (Binance Hot)
Chain: Ethereum
Value: 500 ETH

AI Reasoning:
1. This wallet usually moves to exchanges right before it sells
2. Correlated with 2 other whale deposits in the last 30 min
3. Pattern matches behavior seen before the March drawdown

Predicted impact: BEARISH
What to watch: follow-up deposits from linked wallets
```

**Signal types:**

| Signal | Meaning |
|---|---|
| Accumulation | Whale receiving significant funds |
| Distribution | Whale sending / selling |
| CEX Deposit | Funds moving to exchange — potential sell |
| CEX Withdrawal | Funds leaving exchange — potential buy |
| Large Transfer | A high-value move between wallets |
| Unusual Activity | A wallet breaking its usual pattern |

---

## Part 7 — Common Docker Commands

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# View live logs
docker compose logs -f sentrycage

# Restart tracker only
docker compose restart sentrycage

# Rebuild after code changes
docker compose build sentrycage && docker compose up -d

# Open a shell inside the container
docker compose exec sentrycage bash

# Pull a different Ollama model
docker compose exec ollama ollama pull mistral:7b

# Check resource usage
docker stats
```

---

## Part 8 — Troubleshooting

**No Telegram message after startup**

1. Make sure you sent `/start` to your bot before running the tracker.
2. Check the bot token and chat ID are correct in `.env`.
3. Inspect the logs: `docker compose logs sentrycage | grep -i telegram`

**Ollama timeout / AI reasoning disabled**

AI reasoning is optional — if Ollama is slow or unavailable, the tracker falls back to rule-based signals automatically. To fix Ollama:

```bash
docker compose exec ollama ollama pull llama3.1:8b
# verify it's reachable:
curl http://localhost:11434/api/tags
```

**Out of memory with Ollama**

Switch to a smaller model:

```env
OLLAMA_MODEL=mistral:7b
```

Or use a cloud provider instead (`LLM_PROVIDER=claude`).

**A test fails on my machine**

The 75 tests pass on a clean install — a failure is almost always the environment,
not the code: wrong Python version (use 3.9+, tested on 3.12), a missing dependency
(`pip install -r requirements.txt`), or no network during a test that reaches out.
Run `pytest -v` to see which one, and check the matching item above. The core
tracker is deliberately resilient: if the local AI model is too heavy for your RAM
it drops to rule-based signals — you keep getting alerts either way.

---

## Part 9 — Running Tests

```bash
# All tests (75 passing — full suite green)
pytest

# With coverage report
pytest --cov=src --cov-report=term-missing

# Test your LLM provider connection
docker compose run --rm sentrycage python scripts/test_llm.py

# Benchmark provider performance
docker compose run --rm sentrycage python scripts/benchmark_providers.py
```

---

## Part 10 — Updating

```bash
git pull
docker compose build sentrycage
docker compose up -d
```

Your wallet database and signal history are stored in a Docker volume (`sentrycage-data`) and survive updates.

---

**Disclaimer:** SentryCage is a monitoring and analysis tool. It does not execute trades. Signals are not financial advice.
