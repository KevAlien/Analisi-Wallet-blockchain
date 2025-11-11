# 🧠 AI Reasoning Agent - Complete Guide

## 🎉 What Was Implemented

Your Whale Tracker now has a **fully integrated AI Reasoning Agent** with:

### 1. **Modular LLM Architecture**
- ✅ Abstract interface supporting multiple providers
- ✅ **Ollama** (local Docker) - Recommended
- ✅ **LMStudio** (local host) - For GUI control
- ✅ **Claude** (cloud) - Best quality, large context
- ✅ **OpenAI** (cloud) - Reliable alternative
- ✅ Automatic fallback chain (tries providers in order)

### 2. **Reasoning Loop System**
- ✅ Multi-step analysis with context awareness
- ✅ Circuit breakers to prevent infinite loops
- ✅ Timeout protection (configurable)
- ✅ Graceful fallback to rule-based analysis

### 3. **Analysis Tools Ecosystem**
- ✅ **Historical Pattern Analyzer** - Learns wallet behavior
- ✅ **Cross-Chain Correlator** - Detects multi-chain patterns
- ✅ **Market Context Fetcher** - Integrates price/volume data
- ✅ **Wallet Profiler** - Classifies trading styles

### 4. **Enhanced Signals**
- ✅ Reasoning chains (step-by-step explanation)
- ✅ Predicted market impact (bullish/bearish/neutral)
- ✅ Recommended actions (what to do next)
- ✅ Correlation data (related events)
- ✅ Market context (current conditions)

### 5. **Production-Ready Features**
- ✅ Context memory (stores last 100 events, 24h retention)
- ✅ Batch processing (analyzes multiple transactions together)
- ✅ Error handling with automatic fallback
- ✅ Comprehensive logging
- ✅ Performance metrics

### 6. **Docker Containerization**
- ✅ Complete docker-compose setup
- ✅ Integrated Ollama service
- ✅ Auto model download
- ✅ Support for host LMStudio
- ✅ GPU support (optional)

### 7. **Testing & Utilities**
- ✅ Interactive setup wizard (`scripts/setup.sh`)
- ✅ LLM provider test suite (`scripts/test_llm.py`)
- ✅ Performance benchmark tool (`scripts/benchmark_providers.py`)

---

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# 1. Setup
chmod +x scripts/setup.sh
./scripts/setup.sh

# 2. Configure API keys in .env
nano .env

# 3. Start
docker-compose up -d

# 4. View logs
docker-compose logs -f whale-tracker
```

### Option 2: Manual (with Ollama)

```bash
# 1. Install Ollama
curl https://ollama.ai/install.sh | sh

# 2. Download model
ollama pull llama3.1:8b

# 3. Configure
cp .env.example .env
# Edit .env with your keys
nano .env

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run
python main.py
```

---

## 🎛️ Configuration

### Choose Your LLM Provider

Edit `.env`:

```env
# Local (Free, no API key needed)
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.1:8b

# Or use LMStudio
LLM_PROVIDER=lmstudio
LMSTUDIO_URL=http://localhost:1234/v1

# Or use Claude (best quality)
LLM_PROVIDER=claude
CLAUDE_API_KEY=sk-ant-...

# Or use OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

### Adjust Reasoning Parameters

```env
# Enable/disable AI reasoning
ENABLE_REASONING=true

# Max reasoning iterations
MAX_REASONING_ITERATIONS=5

# Timeout in seconds
REASONING_TIMEOUT=30
```

### Disable AI (Rule-Based Only)

```env
ENABLE_REASONING=false
```

The system will work with traditional pattern matching.

---

## 📊 How It Works

### Without AI (Traditional):
```
Transaction → Rule-Based Analysis → Basic Signal → Telegram
```

### With AI (Enhanced):
```
Transaction → Context Memory
            ↓
            Historical Analysis
            Cross-Chain Correlation
            Market Context
            Wallet Profiling
            ↓
            AI Reasoning Loop (max 5 iterations)
            ↓
            Enhanced Signal with Reasoning → Telegram
```

### Reasoning Loop Example:

**Iteration 1:** Gather context
- Check wallet history
- Find cross-chain correlations
- Get current market conditions
- Profile wallet behavior

**Iteration 2:** AI Analysis
- LLM analyzes all context
- Generates reasoning chain
- Predicts impact
- Recommends actions

**Iteration 3:** Validation
- Verify confidence threshold
- Check for anomalies
- Store in memory

**Output:** Enhanced signal with full reasoning

---

## 🧪 Testing

### Test All Providers

```bash
# In Docker
docker-compose run --rm whale-tracker python scripts/test_llm.py

# Manual
python scripts/test_llm.py
```

Output shows which providers are available and working.

### Benchmark Performance

```bash
# Compare speed of different providers
docker-compose run --rm whale-tracker python scripts/benchmark_providers.py
```

Shows latency, tokens/sec, and recommendations.

### Test Mode

```bash
# Send test signal to verify Telegram
python main.py --test
```

---

## 💡 Cost Comparison

| Provider | Cost | Speed | Quality | Setup |
|----------|------|-------|---------|-------|
| **Ollama** | Free | Medium | Good | Easy (Docker) |
| **LMStudio** | Free | Medium | Good | Medium (Manual) |
| **Claude** | ~$3/day | Fast | Excellent | Easy (API key) |
| **OpenAI** | ~$2-5/day | Fast | Very Good | Easy (API key) |

**Recommendation:** Start with Ollama (free) → upgrade to Claude if you need better quality.

---

## 🔧 Troubleshooting

### AI reasoning not working?

```bash
# Check which provider is active
docker-compose logs whale-tracker | grep "AI Reasoning"

# Test providers
docker-compose run --rm whale-tracker python scripts/test_llm.py
```

### Ollama model not downloading?

```bash
# Check Ollama logs
docker-compose logs ollama

# Manually pull model
docker-compose exec ollama ollama pull llama3.1:8b

# List models
docker-compose exec ollama ollama list
```

### Out of memory?

Use a smaller model:
```env
OLLAMA_MODEL=mistral:7b  # Only 6GB
```

Or increase Docker memory:
- Docker Desktop → Settings → Resources → Memory

### Fallback to rule-based?

This is normal if:
- ✅ LLM not available
- ✅ Request timed out (>30s)
- ✅ Too many consecutive failures (>3)

Check logs for specific error.

---

## 📈 Performance Tips

1. **Batch Processing**: The system automatically batches significant transactions
2. **Circuit Breaker**: After 3 failures, falls back to rule-based for safety
3. **Context Memory**: Keeps last 100 events for faster correlation
4. **Caching**: Market data cached for 60 seconds
5. **Timeout Protection**: Max 30s per analysis (configurable)

---

## 🎯 What's Next?

### Potential Improvements:
- [ ] Add more chains (Polygon, BSC, etc.)
- [ ] Implement sentiment analysis from news/social media
- [ ] Add backtesting framework
- [ ] Create web UI for configuration
- [ ] Implement ML model for pattern recognition
- [ ] Add portfolio tracking integration

### Contributing:
Feel free to open issues or PRs at:
https://github.com/KevAlien/Analisi-Wallet-blockchain

---

## 📚 Documentation

- **README.md** - Overview and features
- **DOCKER_SETUP.md** - Detailed Docker guide
- **AI_REASONING_GUIDE.md** - This file
- **.env.example** - Configuration reference

---

## 🙏 Credits

Built with:
- **LangChain** inspiration for tool ecosystem
- **Anthropic Claude** for high-quality reasoning
- **Ollama** for local LLM deployment
- **Docker** for containerization

---

**Questions?** Open an issue on GitHub!

**Like this project?** Star it! ⭐

**Donations:**
`0x2ab7e808fa5024efe1253cbf0592762ecce7e834`
