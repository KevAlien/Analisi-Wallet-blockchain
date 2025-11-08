Project Brief: Whale & Market Maker Tracking Bot

Objective: Build a Telegram bot that tracks market makers’ and whales’ wallets on blockchain explorers (e.g., Ethereum, Arbitrum) and delivers real-time market signals for trading.

Core Features:  
1. Wallet Monitoring  
   - Track specific wallets (market makers and whales) on explorers like Etherscan or Arbiscan.  
   - Analyze in/out transactions to detect large money flows.  
   - Dynamic wallet database (manually updatable or pattern-based).

2. Real-Time Indicators  
   - Telegram notifications with:  
     - Significant transaction volumes.  
     - Fund direction (e.g., to DEX, CEX, or staking).  
     - Wallet balance % changes.  
   - Human-readable signals (e.g., "Whale X moves $1M to Uniswap").

3. Automated Trading  
   - Long/short options on integrated platforms (e.g., Binance, dYdX).  
   - Logic:  
     - Funds to DEX = long on relevant tokens.  
     - Mass withdrawals = short or bearish alert.  
   - Order execution: user-approved or automated (configurable).

Technical Requirements:  
- Language: Python (or Node.js).  
- APIs: Blockchain explorers (Etherscan, Arbiscan), Telegram Bot API, exchange APIs.  
- On-chain data parsing with web3.py or ethers.js.  
- Markdown output on Telegram (e.g., Long ETH - Whale Y active).  

Deliverables:  
- Bot deployed on a server (e.g., Heroku/AWS).  
- Commented, scalable code.  
- Instructions for adding wallets to track.

Telegram Handle: Send output to @Moomsbot for feedback.

---