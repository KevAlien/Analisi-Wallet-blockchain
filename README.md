# 🐋 Blockchain Wallet Analysis with AI Reasoning

An advanced tool for tracking whale and market maker wallet activities on Ethereum and Arbitrum. Features **AI-powered reasoning** to analyze transaction flows, detect patterns, and generate intelligent trading signals delivered via Telegram.

## ✨ What's New: AI Reasoning Agent

- **🤖 Multiple LLM Backends**: Supports Ollama (local), LMStudio (local), Claude, and OpenAI
- **🧠 Intelligent Analysis**: AI reasoning loops correlate multi-chain events and historical patterns
- **📊 Enhanced Signals**: Detailed reasoning chains explain WHY a signal was generated
- **🔄 Automatic Fallback**: Gracefully falls back to rule-based analysis if LLM unavailable
- **⚡ Optimized for Speed**: Batch processing and circuit breakers prevent delays
- **🐳 Docker Ready**: Complete containerization with Ollama included

## 🎯 Features

### Core Features
- ✅ Monitor whale and market maker wallet transactions
- ✅ Analyze transaction patterns and fund flows
- ✅ Generate trading signals based on significant movements
- ✅ Deliver alerts via Telegram bot
- ✅ Support for Ethereum and Arbitrum blockchains

### AI-Powered Analysis
- 🤖 **Reasoning Loop**: Multi-step analysis with context awareness
- 🔗 **Cross-Chain Correlation**: Detect coordinated movements across chains
- 📈 **Historical Pattern Recognition**: Learn from wallet behavior history
- 🎯 **Market Context Integration**: Factor in current market conditions
- 💡 **Actionable Recommendations**: Get suggested actions with each signal
- 🧠 **Transparent Reasoning**: See the AI's thought process step-by-step

## Project Structure

```
blockchain-wallet-analysis/
├── Memory-Bank/              # Project memory and documentation
├── src/                      # Source code
│   ├── analysis/             # Transaction analysis code
│   ├── config/               # Configuration files
│   ├── fetching/             # Blockchain data fetching
│   ├── notifications/        # Notification delivery
│   ├── signals/              # Signal generation
│   └── utils/                # Utility functions
├── tests/                    # Test files
├── .env.example              # Environment variables template
├── main.py                   # Main entry point
└── requirements.txt          # Python dependencies
```

## 🚀 Quick Start (Docker - Recommended)

### Prerequisites
- Docker & Docker Compose
- API keys (Etherscan V2, Infura, Telegram)

### Setup

```bash
# 1. Clone repository
git clone https://github.com/KevAlien/Analisi-Wallet-blockchain.git
cd Analisi-Wallet-blockchain

# 2. Run setup script
chmod +x scripts/setup.sh
./scripts/setup.sh

# 3. Configure .env with your API keys
nano .env

# 4. Start services
docker-compose up -d

# 5. View logs
docker-compose logs -f whale-tracker
```

**That's it!** The system will:
- ✅ Download Ollama and llama3.1:8b model automatically
- ✅ Start monitoring whale wallets
- ✅ Send AI-enhanced signals to your Telegram

**For detailed Docker setup:** See [DOCKER_SETUP.md](DOCKER_SETUP.md)

## 💻 Installation (Manual)

<details>
<summary>Click to expand manual installation steps</summary>

1. Clone the repository
   ```bash
   git clone https://github.com/KevAlien/Analisi-Wallet-blockchain.git
   cd Analisi-Wallet-blockchain
   ```

2. Create and activate a virtual environment
   ```bash
   python -m venv venv
   ```

   **Activate the virtual environment:**
   ```bash
   # On Windows (Command Prompt)
   venv\Scripts\activate.bat

   # On Windows (PowerShell)
   venv\Scripts\Activate.ps1

   # On macOS/Linux
   source venv/bin/activate
   ```

   **Important for Windows PowerShell users:**
   If you get an execution policy error, run this first:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

   **Verify you're in the virtual environment:**
   ```bash
   # You should see (venv) in your terminal prompt
   # Check Python location:
   which python    # macOS/Linux
   where python    # Windows

   # The path should point to your venv directory
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

   **Note:** This project requires Python 3.9-3.12. Python 3.13 is not yet fully supported due to pandas/numpy compatibility.

4. Set up environment variables
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

5. (Optional) Install local LLM
   - **Ollama**: [Download](https://ollama.ai) and run `ollama pull llama3.1:8b`
   - **LMStudio**: [Download](https://lmstudio.ai) and load a model

</details>

## 📱 Example AI-Enhanced Signal

**Traditional Rule-Based Alert:**
```
🔴 DISTRIBUTION SIGNAL ⭐⭐⭐
💰 Value: 500.00 ETH
👛 Wallet: 0xabc...def (whale)
⛓️ Chain: Ethereum
```

**AI-Enhanced Alert with Reasoning:**
```
🔴 DISTRIBUTION SIGNAL ⭐⭐⭐⭐
💰 Value: 500.00 ETH
👛 Wallet: Vitalik Buterin (whale)
⛓️ Chain: Ethereum

🧠 AI REASONING:
  1. Wallet historically accumulates during dips, sells during pumps
  2. This deposit to Binance follows 15% price increase in last 48h
  3. Correlated with 2 other whale deposits within 30 minutes
  4. Market context: Strong bullish trend, high volume
  5. Pattern matches historical behavior before -20% corrections

📈 Predicted Impact: BEARISH
💡 Recommended Actions:
  • Monitor for additional whale deposits in next 2 hours
  • Consider reducing long exposure
  • Watch for price action near $3,500 support

🔗 Correlations:
  • Whale B deposited 300 ETH to Coinbase 15 min ago
  • Arbitrum whale activity increased 40% in last hour
```

## API Keys Required

- **Etherscan API Key (V2)**: Sign up at [Etherscan](https://etherscan.io/apis)
  - Single API key now works across all 60+ supported chains (Ethereum, Arbitrum, Base, etc.)
  - No need for separate Arbiscan API key anymore
- **Telegram Bot Token**: Create a bot using [BotFather](https://t.me/botfather)
- **Infura API Key**: Sign up at [Infura](https://infura.io/) for blockchain RPC endpoints

## Usage

### Running the application

```
python main.py
```

### Test mode

To verify that all components are working:

```
python main.py --test
```

## Adding Wallet Addresses

Edit `src/config/wallet_registry.py` to add or modify wallet addresses to track.

## Signal Types

The system generates the following types of signals:

- **Accumulation**: Whale wallet receiving significant funds
- **Distribution**: Whale wallet sending significant funds
- **Transfer**: Transfer between tracked wallets
- **Exchange Deposit**: Deposit to exchange (potential sell)
- **Exchange Withdrawal**: Withdrawal from exchange (potential buy)
- **Unusual Activity**: Unusual patterns detected

## Development

### Running tests

```
pytest
```

### Coding Standards

This project follows PEP 8 style guidelines. You can verify your code with:

```
flake8 src/
```

## Future Enhancements

- Add support for more EVM-compatible chains
- Implement machine learning for pattern recognition
- Enhance transaction categorization algorithms
- Add web UI for configuration and monitoring
- Implement historical analysis of wallet behaviors

## License

[MIT License](LICENSE)

## Donations Address

If you appreciate what i do, you can support by donating here:
- 0x2ab7e808fa5024efe1253cbf0592762ecce7e834