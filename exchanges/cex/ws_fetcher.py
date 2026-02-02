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
from utils.rpc_manager import get_global_session

logger = get_logger(__name__)

@dataclass
class WSPrice:
    exchange: str
    symbol: str
    bid: float
    ask: float
    timestamp: float
    seq: int = 0

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
        # Top-tier exchanges with reliable WebSocket support
        WS_SUPPORTED = [
            "binance", "bybit", "okx", "gateio", "kucoin", 
            "mexc", "kraken", "whitebit", "bitget", "htx", 
            "phemex", "bitmart", "lbank"
        ]
        
        for config in EXCHANGES:
            if config.id in WS_SUPPORTED:
                try:
                    session = await get_global_session()
                    exchange_class = getattr(ccxt, config.id)
                    # CCXT Pro exchanges
                    self._exchanges[config.id] = exchange_class({
                        'enableRateLimit': True,
                        'options': {'defaultType': 'spot'},
                        'session': session,
                        'newUpdates': True
                    })
                    self._latest_prices[config.id] = {}
                    logger.info(f"Initialized WebSocket for {config.name}")
                except Exception as e:
                    logger.error(f"Failed to init WS for {config.id}: {e}")

    async def _watch_exchange_tickers(self, exchange_id: str, symbols: List[str]):
        """Continuous loop to watch tickers via WebSocket"""
        exchange = self._exchanges[exchange_id]
        
        # Pre-filter symbols that exist in market
        valid_symbols = []
        for s in symbols:
            if s in exchange.markets:
                valid_symbols.append(s)
            else:
                # Try common variations
                parts = s.split('/')
                if len(parts) == 2:
                    vars = [f"{parts[0]}{parts[1]}", f"{parts[0]}-{parts[1]}"]
                    for var in vars:
                        if var in exchange.markets:
                            valid_symbols.append(var)
                            break
        
        if not valid_symbols:
            return

        # Optimization: Limit symbols per connection if needed
        # CCXT Pro handles many, but let's be safe.
        max_symbols = 250
        hot_symbols = valid_symbols[:max_symbols]

        while self._running:
            try:
                # watch_tickers returns a dict of all symbols that updated
                tickers = await exchange.watch_tickers(hot_symbols)
                
                for symbol, ticker in tickers.items():
                    bid = ticker.get('bid')
                    ask = ticker.get('ask')
                    
                    if not bid or not ask or bid <= 0 or ask <= 0:
                        continue
                        
                    # Normalize back for internal pricing matrix
                    norm_symbol = symbol
                    if symbol in exchange.markets:
                        norm_symbol = exchange.markets[symbol].get('symbol', symbol)
                    
                    self._latest_prices[exchange_id][norm_symbol] = WSPrice(
                        exchange=exchange_id,
                        symbol=norm_symbol,
                        bid=float(bid),
                        ask=float(ask),
                        timestamp=ticker['timestamp'] / 1000.0 if ticker.get('timestamp') else datetime.now().timestamp()
                    )
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(5) 

    async def start(self, symbols: Optional[List[str]] = None):
        """Start all WebSocket streams"""
        if self._running:
            return
            
        self._running = True
        
        # Default to TRADING_PAIRS if no symbols provided
        if not symbols:
            symbols = [f"{normalize_symbol(b)}/{normalize_symbol(q)}" for b, q in TRADING_PAIRS]
        
        for exchange_id in self._exchanges:
            task = asyncio.create_task(self._watch_exchange_tickers(exchange_id, symbols))
            self._tasks.append(task)
            
        logger.info(f"Real-time WS streaming started for {len(self._exchanges)} exchanges")

    async def stop(self):
        """Stop all streams"""
        self._running = False
        for task in self._tasks:
            task.cancel()
        
        # Wait for tasks to finish
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks = []
            
        for exchange in self._exchanges.values():
            try:
                await exchange.close()
            except:
                pass
        
        logger.info("WebSocket streams stopped")

    def get_latest_price(self, exchange_id: str, symbol: str) -> Optional[WSPrice]:
        """Get the last seen price from cache (O(1) access)"""
        return self._latest_prices.get(exchange_id, {}).get(symbol)

# Global instance for HFT
ws_fetcher = CCXTProFetcher()
