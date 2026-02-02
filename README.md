# Crypto Arbitrage Scanner

A high-performance, multi-chain cryptocurrency arbitrage scanner that monitors DEXs and CEXs for price discrepancies.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the scanner
python main.py
```

## Features
- 10+ CEXs via CCXT (Binance, Coinbase, Kraken, etc.)
- 9 DEXs across 4 chains (Ethereum, BSC, Polygon, Arbitrum)
- Real-time gas fee estimation
- Terminal dashboard with color-coded alerts
- $5 minimum profit threshold after fees

## Requirements
- Python 3.11+
- No API keys required (uses public endpoints)
