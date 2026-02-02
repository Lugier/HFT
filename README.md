# ⚡ Crypto Arbitrage Scanner Pro (HFT Edition)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![DEX Support](https://img.shields.io/badge/DEX-Uniswap%20V2%2FV3-orange.svg)]()
[![CEX Support](https://img.shields.io/badge/CEX-28+%20Exchanges-green.svg)]()

A high-performance, professional-grade cryptocurrency arbitrage scanner designed for **Spatial Arbitrage** across 16+ blockchains and 28+ centralized exchanges. Engineered for speed using a hybrid WebSocket/REST architecture.

---

## 🚀 Key Features

*   **⚡ HFT Ready:** Ultra-low latency price streaming via **WebSockets (CCXT Pro)** for top-tier exchanges (Binance, Bybit, OKX, etc.).
*   **🌐 Multi-Chain Coverage:** Scans 16+ EVM-compatible chains including Ethereum, Arbitrum, Optimism, BSC, Polygon, Base, Cronos, Moonbeam, and more.
*   **🛠 Advanced DEX Integration:** Support for **Uniswap V2** (and clones like SushiSwap, PancakeSwap) and **Uniswap V3** (multi-fee tier quoter).
*   **📈 Intelligent Slippage Protection:** Real-time price impact calculation based on DEX liquidity reserves and CEX order book estimates.
*   **⛽ Precise Gas Estimation:** Dynamic gas cost calculation across all L1 and L2 networks, including L2 execution fee buffers.
*   **🖥 Beautiful TUI:** Real-time dashboard built with `Rich` for clear tracking of profitable opportunities, stats, and network health.
*   **🛡 Risk Management:** Built-in "Delta-Neutral" strategy support, minimum profit thresholds, and stale data filtering.

---

## 🏗 Technology Stack

- **Core:** Python 3.10+ / Asyncio
- **CEX:** CCXT / CCXT Pro (WebSockets)
- **DEX:** Web3.py (Async)
- **UI:** Rich (Terminal User Interface)
- **RPC:** Custom Failover RPC Manager with Latency Tracking

---

## ⚙️ Quick Start

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/Lugier/HFT.git
cd HFT

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration
Copy the `.env.example` to `.env` and configure your settings:
```bash
cp .env.example .env
```
*Note: Public RPCs are already configured in `config/chains.py`. You only need to add private keys/API keys if you wish to enable execution.*

### 3. Usage
Run the scanner:
```bash
python main.py
```

---

## 📊 How it Works

### 1. Hybrid Price Fetching
The scanner utilizes a dual-mode system:
- **WebSocket (Tier-1):** Instant updates from high-volume exchanges (Binance, Bybit, OKX).
- **REST (Tier-2):** Periodic polling for secondary exchanges to ensure broad market coverage.

### 2. Profit Calculation Formula
The engine doesn't just look at mid-market prices. It calculates:
`Net Profit = (Market Spread - Slippage) - (Gas Fees) - (Withdrawal/Transfer Fees)`

### 3. Inventory-Based Strategy
Designed for capital efficiency: Instead of moving funds across networks for every trade, the engine is built for a delta-neutral setup where you maintain balances on multiple sides (DEX/CEX) and execute swaps/hedges simultaneously.

---

## 🛣 Roadmap

- [x] WebSocket Integration (CCXT Pro)
- [x] Uniswap V3 Support
- [x] Multi-Chain RPC Failover
- [ ] Intra-Exchange Triangular Arbitrage Module
- [ ] MEV Protection (Flashbots integration)
- [ ] Auto-Execution Module for Delta-Neutral Trades

---

## 📄 Disclaimer

**Trading involves significant risk.** This software is for educational and research purposes only. The creators are not responsible for any financial losses. Always test with "Dry Run" mode enabled before committing real capital.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

**Built with ❤️ for the HFT community.**
