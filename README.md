# Blockchain Wallet Analysis

A tool for tracking whale and market maker wallet activities on Ethereum and Arbitrum, analyzing transaction flows, and generating real-time trading signals delivered via Telegram.

## Features

- Monitor whale and market maker wallet transactions
- Analyze transaction patterns and fund flows
- Generate trading signals based on significant movements
- Deliver alerts via Telegram bot
- Support for Ethereum and Arbitrum blockchains

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

## Installation

1. Clone the repository
   ```
   git clone https://github.com/yourusername/blockchain-wallet-analysis.git
   cd blockchain-wallet-analysis
   ```

2. Create and activate a virtual environment
   ```
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables
   ```
   cp .env.example .env
   ```
   Edit the `.env` file with your API keys and configuration.

## API Keys Required

- **Etherscan API Key**: Sign up at [Etherscan](https://etherscan.io/apis)
- **Arbiscan API Key**: Sign up at [Arbiscan](https://arbiscan.io/apis)
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
