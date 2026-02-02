"""
CCXT-based centralized exchange price fetcher
Fetches prices from multiple CEXs using public APIs (no API key required)
"""
import asyncio
from dataclasses import dataclass
from typing import Optional
import ccxt.async_support as ccxt

from config.exchanges import EXCHANGES, ExchangeConfig
from config.tokens import TRADING_PAIRS, normalize_symbol
from utils.rate_limiter import rate_limiter
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CEXPrice:
    """Price data from a CEX"""
    exchange: str
    symbol: str  # e.g., "ETH/USDT"
    bid: float  # Best bid (buy) price
    ask: float  # Best ask (sell) price
    mid: float  # Mid price
    timestamp: int
    volume_24h: Optional[float] = None
    
    @property
    def spread_pct(self) -> float:
        """Calculate spread as percentage"""
        if self.bid == 0:
            return 0
        return ((self.ask - self.bid) / self.bid) * 100


class CCXTFetcher:
    """
    Fetches prices from centralized exchanges using CCXT
    Uses only public APIs (no authentication required)
    """
    
    def __init__(self):
        self._exchanges: dict[str, ccxt.Exchange] = {}
        self._initialized = False
        self._init_semaphore = asyncio.Semaphore(3)  # Lower concurrency to avoid congestion checks
    
    async def initialize(self):
        """Initialize all configured exchanges in parallel"""
        if self._initialized:
            return

        tasks = []
        for config in EXCHANGES:
            tasks.append(self._init_exchange(config))
        
        await asyncio.gather(*tasks)
        self._initialized = True
        logger.info(f"CEX Fetcher ready: {len(self._exchanges)} exchanges")

    async def _init_exchange(self, config: ExchangeConfig):
        """Initialize a single exchange with timeout and cleanup"""
        exchange = None
        try:
            async with self._init_semaphore:
                exchange_class = getattr(ccxt, config.id)
                exchange = exchange_class({
                    'enableRateLimit': False,  # We handle rate limits globally
                    'timeout': 15000, # Increased timeout
                    'options': {'defaultType': 'spot'}, # Default to spot
                })
                
                # Retry loop
                for attempt in range(1, 4):
                    try:
                        # Load markets with timeout
                        await asyncio.wait_for(exchange.load_markets(), timeout=25.0)
                        self._exchanges[config.id] = exchange
                        logger.info(f"✓ Initialized {config.name}")
                        return # Success
                    except Exception as attempt_err:
                        if attempt == 3:
                            raise attempt_err # Propagate on last attempt
                        logger.debug(f"Retrying {config.name} (Attempt {attempt}/3)...")
                        await asyncio.sleep(1.0 * attempt) # Backoff
            
        except Exception as e:
            error_type = type(e).__name__
            logger.warning(f"⚠ Failed to initialize {config.name}: {error_type} - {str(e)[:100]}...")
            if exchange:
                try:
                    await exchange.close()
                except:
                    pass
    
    async def close(self):
        """Close all exchange connections"""
        for exchange in self._exchanges.values():
            await exchange.close()
    
    def _get_symbol(self, exchange: ccxt.Exchange, base: str, quote: str) -> Optional[str]:
        """Get the correct symbol format for an exchange"""
        # Normalize wrapped tokens
        base = normalize_symbol(base)
        quote = normalize_symbol(quote)
        
        # Try mapped symbols first
        # (This is a simplified check, ideally we cache this map)
        target = f"{base}/{quote}"
        if target in exchange.markets:
            return target
            
        # Common variations
        variations = [
            f"{base}/{quote}",
            f"{base}-{quote}",
            f"{base}{quote}",
            f"{base}USDT" if quote == "USDT" else None,
            f"{base}USD" if quote == "USDT" else None,
            f"{base}_USDT" if quote == "USDT" else None,
        ]
        
        for var in variations:
            if var and var in exchange.markets:
                return var
        
        return None
    
    async def fetch_price(
        self,
        exchange_id: str,
        base: str,
        quote: str
    ) -> Optional[CEXPrice]:
        """Fetch price for a single pair from a single exchange"""
        if exchange_id not in self._exchanges:
            return None
        
        exchange = self._exchanges[exchange_id]
        symbol = self._get_symbol(exchange, base, quote)
        
        if not symbol:
            return None
        
        try:
            # Rate limit
            await rate_limiter.acquire(f"cex:{exchange_id}")
            
            ticker = await exchange.fetch_ticker(symbol)
            
            bid = ticker.get('bid') or 0
            ask = ticker.get('ask') or 0
            
            if bid <= 0 or ask <= 0:
                return None
            
            return CEXPrice(
                exchange=exchange_id,
                symbol=f"{normalize_symbol(base)}/{normalize_symbol(quote)}",
                bid=float(bid),
                ask=float(ask),
                mid=(float(bid) + float(ask)) / 2,
                timestamp=ticker.get('timestamp') or 0,
                volume_24h=ticker.get('quoteVolume')
            )
            
        except Exception as e:
            logger.debug(f"Failed to fetch {symbol} from {exchange_id}: {e}")
            return None
    
    async def fetch_all_prices(
        self,
        pairs: Optional[list[tuple[str, str]]] = None,
        exclude_exchanges: Optional[list[str]] = None
    ) -> dict[str, list[CEXPrice]]:
        """
        Fetch prices for all pairs from all exchanges
        Returns dict: symbol -> list of prices from different exchanges
        """
        if not self._initialized:
            await self.initialize()
        
        if pairs is None:
            pairs = TRADING_PAIRS
        
        results: dict[str, list[CEXPrice]] = {}
        # Initialize result lists
        for base, quote in pairs:
            symbol = f"{normalize_symbol(base)}/{normalize_symbol(quote)}"
            results[symbol] = []
        
        # Group by exchange to use batch fetching
        tasks = []
        
        
        for exchange_id, exchange in self._exchanges.items():
            # Skip excluded exchanges (e.g. those handled by WebSocket)
            if exclude_exchanges and exchange_id in exclude_exchanges:
                continue

            # Find valid symbols for this exchange
            exchange_symbols = []
            symbol_map = {} # exchange_symbol -> normalized_symbol
            
            for base, quote in pairs:
                ex_symbol = self._get_symbol(exchange, base, quote)
                if ex_symbol:
                    exchange_symbols.append(ex_symbol)
                    normalized = f"{normalize_symbol(base)}/{normalize_symbol(quote)}"
                    symbol_map[ex_symbol] = normalized
            
            if exchange_symbols:
                tasks.append(self._fetch_exchange_batch(exchange_id, exchange_symbols, symbol_map))
        
        # Execute all batches concurrently
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Merge results
        for batch in batch_results:
            if isinstance(batch, dict):
                for norm_symbol, price in batch.items():
                    if norm_symbol in results:
                        results[norm_symbol].append(price)
        
        return results

    async def _fetch_exchange_batch(
        self, 
        exchange_id: str, 
        symbols: list[str], 
        symbol_map: dict[str, str]
    ) -> dict[str, CEXPrice]:
        """Helper to fetch a batch and map back to normalized symbols"""
        try:
            # Use existing batch fetcher
            prices = await self.fetch_ticker_batch(exchange_id, symbols)
            
            mapped_results = {}
            for ex_symbol, price in prices.items():
                if ex_symbol in symbol_map:
                    # Update the price object with normalized symbol
                    price.symbol = symbol_map[ex_symbol]
                    mapped_results[price.symbol] = price
            return mapped_results
        except Exception as e:
            logger.debug(f"Batch fetch failed for {exchange_id}: {e}")
            return {}
    
    async def fetch_ticker_batch(
        self,
        exchange_id: str,
        symbols: list[str]
    ) -> dict[str, CEXPrice]:
        """
        Fetch multiple tickers from a single exchange in one request
        More efficient than individual requests
        """
        if exchange_id not in self._exchanges:
            return {}
        
        exchange = self._exchanges[exchange_id]
        
        try:
            await rate_limiter.acquire(f"cex:{exchange_id}")
            
            # Filter to only symbols that exist on this exchange
            valid_symbols = [s for s in symbols if s in exchange.markets]
            
            if not valid_symbols:
                return {}
            
            # Some exchanges support fetching all tickers at once
            if exchange.has.get('fetchTickers'):
                tickers = await exchange.fetch_tickers(valid_symbols)
            else:
                # Fall back to individual requests
                tickers = {}
                for symbol in valid_symbols:
                    try:
                        tickers[symbol] = await exchange.fetch_ticker(symbol)
                    except Exception:
                        continue
            
            results = {}
            for symbol, ticker in tickers.items():
                bid = ticker.get('bid') or 0
                ask = ticker.get('ask') or 0
                
                if bid <= 0 or ask <= 0:
                    continue
                
                results[symbol] = CEXPrice(
                    exchange=exchange_id,
                    symbol=symbol,
                    bid=float(bid),
                    ask=float(ask),
                    mid=(float(bid) + float(ask)) / 2,
                    timestamp=ticker.get('timestamp') or 0,
                    volume_24h=ticker.get('quoteVolume')
                )
            
            return results
            
        except Exception as e:
            logger.debug(f"Failed to fetch tickers from {exchange_id}: {e}")
            return {}
    
    def get_available_exchanges(self) -> list[str]:
        """Get list of available exchange IDs"""
        return list(self._exchanges.keys())
    
    def get_available_symbols(self, exchange_id: str) -> list[str]:
        """Get list of available symbols on an exchange"""
        if exchange_id not in self._exchanges:
            return []
        return list(self._exchanges[exchange_id].markets.keys())


# Global instance
cex_fetcher = CCXTFetcher()
