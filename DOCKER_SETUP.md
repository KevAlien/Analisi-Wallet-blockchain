# 🐳 Docker Setup Guide - Whale Tracker with AI Reasoning

Complete guide for running Whale Tracker in Docker with AI-powered reasoning.

## 📋 Prerequisites

- **Docker** (20.10+) - [Install Docker](https://docs.docker.com/get-docker/)
- **Docker Compose** (2.0+) - Usually included with Docker Desktop
- **API Keys** (see Configuration section)

## 🚀 Quick Start

### 1. Clone & Configure

```bash
# Clone the repository
git clone https://github.com/KevAlien/Analisi-Wallet-blockchain.git
cd Analisi-Wallet-blockchain

# Run setup script
chmod +x scripts/setup.sh
./scripts/setup.sh
```

The setup script will:
- ✅ Check Docker installation
- ✅ Create `.env` file from template
- ✅ Let you choose LLM provider
- ✅ Build Docker containers

### 2. Configure API Keys

Edit `.env` file with your keys:

```bash
nano .env  # or use your favorite editor
```

**Required keys:**
```env
ETHERSCAN_API_KEY=your_key_here
ARBISCAN_API_KEY=your_key_here
INFURA_API_KEY=your_key_here
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### 3. Start the System

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f whale-tracker

# Check status
docker-compose ps
```

## 🤖 LLM Provider Options

### Option 1: Ollama (Recommended for Getting Started)

**Pros:** Free, runs in Docker, no API keys needed
**Cons:** Requires GPU/RAM, slower than cloud providers

```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.1:8b
```

**Hardware Requirements:**
- **llama3.1:8b** - 8GB VRAM / 16GB RAM
- **mistral:7b** - 6GB VRAM / 12GB RAM
- **qwen2.5:14b** - 14GB VRAM / 24GB RAM

The first run will download the model (~5GB).

### Option 2: LMStudio (Local on Host)

**Pros:** GUI control, model management
**Cons:** Requires manual setup on host

```env
LLM_PROVIDER=lmstudio
LMSTUDIO_URL=http://host.docker.internal:1234/v1
```

**Setup:**
1. Download [LMStudio](https://lmstudio.ai/)
2. Download a model (llama3.1-8b recommended)
3. Start local server on port 1234
4. Start Whale Tracker

### Option 3: Claude (Cloud)

**Pros:** Best quality, large context (200k tokens)
**Cons:** Costs ~$3/day for active monitoring

```env
LLM_PROVIDER=claude
CLAUDE_API_KEY=sk-ant-...
```

Get API key: https://console.anthropic.com/

### Option 4: OpenAI (Cloud)

**Pros:** Good quality, reliable
**Cons:** Costs ~$2-5/day

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

Get API key: https://platform.openai.com/

## 🧪 Testing

### Test LLM Providers

```bash
# Test all configured providers
docker-compose run --rm whale-tracker python scripts/test_llm.py
```

### Benchmark Performance

```bash
# Compare provider performance
docker-compose run --rm whale-tracker python scripts/benchmark_providers.py
```

### Test Mode

```bash
# Run in test mode (sends test signal)
docker-compose run --rm whale-tracker python main.py --test
```

## 📊 Docker Commands Cheat Sheet

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs (follow)
docker-compose logs -f whale-tracker

# View Ollama logs
docker-compose logs -f ollama

# Restart a service
docker-compose restart whale-tracker

# Rebuild after code changes
docker-compose build whale-tracker

# Check resource usage
docker stats

# Shell into container
docker-compose exec whale-tracker bash

# Pull new model in Ollama
docker-compose exec ollama ollama pull mistral:7b
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `ollama` | Primary LLM provider |
| `ENABLE_REASONING` | `true` | Enable AI reasoning |
| `MAX_REASONING_ITERATIONS` | `5` | Max reasoning loops |
| `REASONING_TIMEOUT` | `30` | Timeout in seconds |
| `POLLING_INTERVAL` | `60` | Check interval (seconds) |
| `TRANSACTION_THRESHOLD` | `50` | Min ETH to alert |

### Disable AI Reasoning

To run in rule-based mode only:

```env
ENABLE_REASONING=false
```

The app will work with basic pattern matching, no LLM needed.

## 🐛 Troubleshooting

### Ollama model not downloading

```bash
# Check Ollama logs
docker-compose logs ollama

# Manually pull model
docker-compose exec ollama ollama pull llama3.1:8b

# List available models
docker-compose exec ollama ollama list
```

### LMStudio not connecting

```bash
# Test from container
docker-compose exec whale-tracker curl http://host.docker.internal:1234/v1/models

# Make sure LMStudio server is running on host
# Check firewall settings
```

### Out of memory errors

```bash
# Check resource usage
docker stats

# Use smaller model
OLLAMA_MODEL=mistral:7b

# Or increase Docker memory limit
# Docker Desktop -> Settings -> Resources
```

### API rate limits

```bash
# Increase polling interval
POLLING_INTERVAL=120

# Or switch to local provider
LLM_PROVIDER=ollama
```

## 🔄 Updates

```bash
# Pull latest code
git pull

# Rebuild containers
docker-compose build

# Restart services
docker-compose up -d
```

## 🗑️ Cleanup

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (deletes Ollama models)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

## 📈 Resource Usage

### Typical Usage:
- **Whale Tracker**: ~200MB RAM
- **Ollama (llama3.1:8b)**: ~8GB RAM + 6GB VRAM
- **Disk**: ~5GB per model

### Optimization Tips:
1. Use Ollama with quantized models (Q4, Q5)
2. Increase `POLLING_INTERVAL` to reduce API calls
3. Use LMStudio if GPU is limited
4. Use Claude/OpenAI for lowest resource usage

## 🆘 Support

**Check logs first:**
```bash
docker-compose logs whale-tracker
```

**Common issues:**
- API keys not configured → Edit `.env`
- LLM not available → Run `test_llm.py`
- No GPU → Use CPU-compatible model or cloud provider
- Connection errors → Check firewall/network settings

---

**Need help?** Open an issue: https://github.com/KevAlien/Analisi-Wallet-blockchain/issues
