"""
WebSocket-based price fetcher (CCXT Pro)
Provides real-time price updates for HFT arbitrage
"""
import asyncio
import ccxt.pro as ccxt
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

from config.exchanges import EXCHANGES, ExchangeConfig
from config.tokens import TRADING_PAIRS, normalize_symbol
from utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class WSPrice:
    exchange: str
    symbol: str
    bid: float
    ask: float
    timestamp: float
    seq: int = 0 # Sequence number for HFT tracking

class CCXTProFetcher:
    """
    HFT WebSocket Fetcher
    Streams real-time tickers from multiple exchanges simultaneously
    """
    
    def __init__(self):
        self._exchanges: Dict[str, ccxt.Exchange] = {}
        self._latest_prices: Dict[str, Dict[str, WSPrice]] = {}
        self._running = False
        self._tasks: List[asyncio.Task] = []

    async def initialize(self):
        """Initialize WebSocket connections"""
        for config in EXCHANGES:
            # Note: Only a subset of exchanges might be needed for high-speed
            # Limit to top-tier for best stability in WS
            if config.id in ["binance", "bybit", "okx", "gateio", "kucoin"]:
                try:
                    exchange_class = getattr(ccxt, config.id)
                    self._exchanges[config.id] = exchange_class({
                        'enableRateLimit': True,
                        'options': {'defaultType': 'spot'}
                    })
                    self._latest_prices[config.id] = {}
                    logger.info(f"Initialized WebSocket for {config.name}")
                except Exception as e:
                    logger.error(f"Failed to init WS for {config.id}: {e}")

    async def _watch_exchange_tickers(self, exchange_id: str, symbols: List[str]):
        """Continuous loop to watch tickers via WebSocket"""
        exchange = self._exchanges[exchange_id]
        
        # Map normalized symbols to exchange specific symbols
        # For simplicity, we assume standard CCXT symbols for now
        # In production, use the same mapping logic as in ccxt_fetcher.py
        
        while self._running:
            try:
                # CCXT Pro watchTickers returns updates as they happen
                tickers = await exchange.watch_tickers(symbols)
                
                for symbol, ticker in tickers.items():
                    bid = ticker.get('bid')
                    ask = ticker.get('ask')
                    
                    # Skip if bid/ask are None or 0
                    if not bid or not ask or bid <= 0 or ask <= 0:
                        continue
                        
                    norm_symbol = symbol # Ideally map back to "ETH/USDT"
                    
                    self._latest_prices[exchange_id][norm_symbol] = WSPrice(
                        exchange=exchange_id,
                        symbol=norm_symbol,
                        bid=float(bid),
                        ask=float(ask),
                        timestamp=ticker['timestamp'] / 1000.0 if ticker.get('timestamp') else datetime.now().timestamp()
                    )
            except Exception as e:
                logger.debug(f"WS Error on {exchange_id}: {e}")
                await asyncio.sleep(5) # Backoff on error

    async def start(self):
        """Start all WebSocket streams"""
        self._running = True
        
        for exchange_id in self._exchanges:
            # Filter trading pairs for this exchange
            symbols = [f"{normalize_symbol(b)}/{normalize_symbol(q)}" for b, q in TRADING_PAIRS]
            
            # Start a dedicated task for this exchange
            task = asyncio.create_task(self._watch_exchange_tickers(exchange_id, symbols))
            self._tasks.append(task)
            
        logger.info(f"Real-time WS streaming started for {len(self._exchanges)} exchanges")

    async def stop(self):
        """Stop all streams"""
        self._running = False
        for task in self._tasks:
            task.cancel()
        
        for exchange in self._exchanges.values():
            await exchange.close()
        
        logger.info("WebSocket streams stopped")

    def get_latest_price(self, exchange_id: str, symbol: str) -> Optional[WSPrice]:
        """Get the last seen price from cache (O(1) access)"""
        return self._latest_prices.get(exchange_id, {}).get(symbol)

# Global instance for HFT
ws_fetcher = CCXTProFetcher()
