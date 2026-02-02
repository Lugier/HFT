"""
Arbitrage Detection Engine
Finds profitable arbitrage opportunities across CEXs and DEXs
"""
import asyncio
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from config.chains import ChainId
from config.tokens import TRADING_PAIRS, normalize_symbol
from config.settings import MIN_PROFIT_USD, DEFAULT_TRADE_SIZE_USD, get_profit_level, ProfitLevel
from exchanges.cex.ccxt_fetcher import cex_fetcher, CEXPrice
from exchanges.cex.ws_fetcher import ws_fetcher
from exchanges.dex.aggregator import dex_aggregator, DEXQuote
from core.gas_estimator import gas_estimator, GasEstimate
from config.fees import get_withdrawal_fee
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PriceSource:
    """Unified price source (CEX or DEX)"""
    source_type: str  # "CEX" or "DEX"
    source_name: str
    chain: Optional[ChainId] = None
    bid: float = 0  # Buy price (we can buy at this price)
    ask: float = 0  # Sell price (we can sell at this price)
    timestamp: float = 0
    volume_24h: Optional[float] = None
    
    @property
    def source_id(self) -> str:
        if self.chain:
            return f"{self.source_name}@{self.chain.name}"
        return self.source_name


@dataclass
class ArbitrageOpportunity:
    """Represents an arbitrage opportunity"""
    symbol: str  # e.g., "ETH/USDT"
    buy_source: PriceSource
    sell_source: PriceSource
    buy_price: float
    sell_price: float
    spread_pct: float
    gross_profit_usd: float
    gas_cost_usd: float
    withdrawal_fee_usd: float
    net_profit_usd: float
    profit_level: Optional[ProfitLevel]
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def is_cross_chain(self) -> bool:
        """Check if this is a cross-chain opportunity"""
        return (
            self.buy_source.chain is not None and
            self.sell_source.chain is not None and
            self.buy_source.chain != self.sell_source.chain
        )
    
    @property
    def involves_dex(self) -> bool:
        """Check if any side involves a DEX"""
        return self.buy_source.source_type == "DEX" or self.sell_source.source_type == "DEX"


class ArbitrageEngine:
    """
    Main arbitrage detection engine
    Scans all price sources and finds profitable opportunities
    """
    
    def __init__(self):
        self._gas_estimates: dict[ChainId, GasEstimate] = {}
        self._last_scan_time: Optional[datetime] = None
        self._total_pairs_checked = 0
        self._opportunities: list[ArbitrageOpportunity] = []
    
    async def initialize(self):
        """Initialize all price fetchers"""
        logger.info("[bold blue]Initializing Arbitrage Engine...[/bold blue]")
        
        # Initialize CEX fetcher (REST)
        await cex_fetcher.initialize()
        
        # Initialize WS fetcher (Real-time)
        await ws_fetcher.initialize()
        await ws_fetcher.start()
        
        # Initialize DEX aggregator
        await dex_aggregator.initialize()
        
        # Get initial gas estimates
        self._gas_estimates = await gas_estimator.get_all_gas_estimates()
        
        logger.info("[bold green]Arbitrage Engine ready![/bold green]")
    
    def _build_price_matrix(
        self,
        cex_prices: dict[str, list[CEXPrice]],
        dex_prices: dict[str, list[DEXQuote]]
    ) -> dict[str, list[PriceSource]]:
        """Build unified price matrix from all sources"""
        matrix: dict[str, list[PriceSource]] = {}
        now = datetime.now().timestamp()
        
        # Add CEX prices
        for symbol, prices in cex_prices.items():
            if symbol not in matrix:
                matrix[symbol] = []
            
            for price in prices:
                # RELIABILITY CHECK: Stale Data (< 10s)
                age = now - (price.timestamp / 1000) # CCXT uses ms
                if age > 10:
                    continue
                    
                # RELIABILITY CHECK: Zombie Pair (< $50k volume)
                # Note: Some exchanges don't report quoteVolume, so we skip check if None
                if price.volume_24h is not None and price.volume_24h < 50000:
                    continue
                
                matrix[symbol].append(PriceSource(
                    source_type="CEX",
                    source_name=price.exchange,
                    bid=price.bid,
                    ask=price.ask,
                    timestamp=price.timestamp / 1000,
                    volume_24h=price.volume_24h
                ))
        
        # Add DEX prices
        for symbol, quotes in dex_prices.items():
            if symbol not in matrix:
                matrix[symbol] = []
            
            for quote in quotes:
                # RELIABILITY CHECK: Stale Data (< 10s)
                if quote.timestamp > 0:
                    age = now - quote.timestamp
                    if age > 10:
                        continue
                
                # Apply fee to bid/ask
                bid = quote.bid * (1 - quote.fee_percent / 100)
                ask = quote.ask * (1 + quote.fee_percent / 100)
                
                matrix[symbol].append(PriceSource(
                    source_type="DEX",
                    source_name=quote.dex_name,
                    chain=quote.chain,
                    bid=bid,
                    ask=ask,
                    timestamp=quote.timestamp
                ))
        
        return matrix
    
    def _estimate_gas_cost(
        self,
        buy_source: PriceSource,
        sell_source: PriceSource
    ) -> float:
        """Estimate gas cost for an arbitrage trade"""
        cost = 0.0
        
        # DEX gas costs (L1/L2 specific)
        if buy_source.source_type == "DEX" and buy_source.chain:
            estimate = self._gas_estimates.get(buy_source.chain)
            if estimate:
                cost += estimate.swap_cost_usd
        
        if sell_source.source_type == "DEX" and sell_source.chain:
            estimate = self._gas_estimates.get(sell_source.chain)
            if estimate:
                cost += estimate.swap_cost_usd
        
        # CEX trading fees (approximate 0.1% or lower with VIP)
        if buy_source.source_type == "CEX":
            cost += DEFAULT_TRADE_SIZE_USD * 0.001
        if sell_source.source_type == "CEX":
            cost += DEFAULT_TRADE_SIZE_USD * 0.001
            
        return cost

    def _estimate_withdrawal_fee(
        self,
        buy_source: PriceSource,
        sell_source: PriceSource
    ) -> float:
        """
        Estimate CEX withdrawal fee
        HFT NOTE: In an Inventory-Based strategy (holding funds on both sides),
        withdrawal fees are 0 during the trade and only occur during daily rebalancing.
        """
        # For pure spatial arb (moving funds), we count it. 
        # For HFT / Inventory arb, we would set this to 0.
        fee = 0.0
        
        if buy_source.source_type == "CEX" and sell_source.source_type == "DEX":
            fee += get_withdrawal_fee(sell_source.chain)
            
        if buy_source.source_type == "CEX" and sell_source.source_type == "CEX":
            fee += 5.0 # Average CEX bridge fee
            
        return fee
    
    def _calculate_slippage_price(self, price: float, source: PriceSource, size_usd: float, is_buy: bool = True) -> float:
        """
        HFT Optimization: Adjust price based on liquidity (Order Book Depth)
        
        Args:
            price: The raw bid/ask price
            source: The price source (CEX/DEX)
            size_usd: Trade size in USD
            is_buy: True if buying (price goes UP due to slippage), False if selling (price goes DOWN)
        """
        # For DEX, slippage is already partially calculated in dex_aggregator (reserve-based)
        # For CEX, we currently use L1 (Top of Book). 
        # TODO: Integrate fetchOrderBook (L2) for higher precision at large sizes.
        
        if source.source_type == "DEX":
            # DEX aggregator already applies impact based on reserves for V2
            return price
            
        # For CEX L1, we assume a tiny fixed slippage for 1k trades
        # Usually < 0.05% for majors, but can be 0.5% for mid-caps
        slippage_factor = 0.0005 # 0.05% default
        
        if source.source_name.lower() in ["binance", "coinbase"]:
            slippage_factor = 0.0002 # Highly liquid
        
        # Buy: you pay more than quoted ask (price goes up)
        # Sell: you receive less than quoted bid (price goes down)
        if is_buy:
            return price * (1 + slippage_factor)
        else:
            return price * (1 - slippage_factor)

    def _find_opportunities(
        self,
        price_matrix: dict[str, list[PriceSource]]
    ) -> list[ArbitrageOpportunity]:
        """Find all arbitrage opportunities in the price matrix"""
        opportunities = []
        
        for symbol, sources in price_matrix.items():
            if len(sources) < 2:
                continue
            
            # Compare all pairs of sources
            for i, buy_source in enumerate(sources):
                for j, sell_source in enumerate(sources):
                    if i == j:
                        continue
                    
                    # 1. SLIPPAGE ADJUSTMENT
                    # Real Buy Price (Ask + Impact) - we pay more
                    buy_price = self._calculate_slippage_price(buy_source.ask, buy_source, DEFAULT_TRADE_SIZE_USD, is_buy=True)
                    # Real Sell Price (Bid - Impact) - we receive less
                    sell_price = self._calculate_slippage_price(sell_source.bid, sell_source, DEFAULT_TRADE_SIZE_USD, is_buy=False)
                    
                    if buy_price <= 0.000001 or sell_price <= 0.000001:
                        continue
                        
                    # Calculate spread
                    spread_pct = ((sell_price - buy_price) / buy_price) * 100
                    
                    if spread_pct <= 0 or spread_pct > 100:
                        continue
                    
                    # 2. COST CALCULATION
                    gross_profit = (spread_pct / 100) * DEFAULT_TRADE_SIZE_USD
                    gas_cost = self._estimate_gas_cost(buy_source, sell_source)
                    withdrawal_fee = self._estimate_withdrawal_fee(buy_source, sell_source)
                    
                    # HFT NOTE on Execution:
                    # If involve_dex and chain == Etheruem, must use FLASHBOTS to avoid MEV Frontrunning.
                    # TODO: Implement core/execution/flashbots_handler.py
                    
                    net_profit = gross_profit - gas_cost - withdrawal_fee
                    
                    # Check if profitable
                    if net_profit < MIN_PROFIT_USD:
                        continue
                    
                    profit_level = get_profit_level(net_profit)
                    
                    opportunities.append(ArbitrageOpportunity(
                        symbol=symbol,
                        buy_source=buy_source,
                        sell_source=sell_source,
                        buy_price=buy_price,
                        sell_price=sell_price,
                        spread_pct=spread_pct,
                        gross_profit_usd=gross_profit,
                        gas_cost_usd=gas_cost,
                        withdrawal_fee_usd=withdrawal_fee,
                        net_profit_usd=net_profit,
                        profit_level=profit_level
                    ))
        
        # Sort by net profit descending
        opportunities.sort(key=lambda x: x.net_profit_usd, reverse=True)
        
        return opportunities
    
    async def scan(self) -> list[ArbitrageOpportunity]:
        """
        Perform a full scan across all sources
        Returns list of profitable opportunities
        """
        scan_start = datetime.now()
        
        # 1. IDENTIFY WS EXCHANGES
        ws_active_exchanges = list(ws_fetcher._exchanges.keys())
        
        # 2. FETCH REST PRICES (Excluding WS exchanges)
        # This will be much faster now as it skips the heavy hitters (Binance etc.)
        cex_task = cex_fetcher.fetch_all_prices(TRADING_PAIRS, exclude_exchanges=ws_active_exchanges)
        
        # Expanded DEX pairs to check
        dex_pairs = [
            # Majors
            ("WETH", "USDT"), ("WETH", "USDC"), ("WETH", "DAI"),
            ("WBTC", "USDT"), ("WBTC", "USDC"), ("WBTC", "WETH"),
            ("WBNB", "USDT"), ("WBNB", "USDC"),
            
            # L1/L2 tokens
            ("WMATIC", "USDT"), ("WMATIC", "USDC"),
            ("WAVAX", "USDT"), ("WAVAX", "USDC"),
            ("WFTM", "USDT"),
            ("ARB", "USDT"), ("ARB", "WETH"),
            ("OP", "USDT"), ("OP", "WETH"),
            
            # DeFi
            ("LINK", "USDT"), ("LINK", "WETH"),
            ("UNI", "USDT"), ("UNI", "WETH"),
            ("AAVE", "USDT"), ("AAVE", "WETH"),
            
            # New Chain tokens
            ("WCRO", "USDT"), ("WCRO", "USDC"),
            ("WGLMR", "USDT"), ("WGLMR", "USDC"),
            ("WCELO", "USDT"), ("WCELO", "USDC"),
            ("WKAVA", "USDT"), ("WKAVA", "USDC"),
            ("ATOM", "USDT"), ("ATOM", "USDC"),
            ("DOT", "USDT"), ("DOT", "USDC"),
            
            # Memes/Other
            ("PEPE", "WETH"), ("SHIB", "USDT")
        ]
        
        dex_task = dex_aggregator.fetch_all_prices(dex_pairs)
        gas_task = gas_estimator.get_all_gas_estimates()
        
        cex_prices, dex_prices, gas_estimates = await asyncio.gather(
            cex_task, dex_task, gas_task
        )
        
        # 3. MERGE WS PRICES INTO CEX PRICES
        # Inject the ultra-low latency WS prices into the result set
        for exchange_id in ws_active_exchanges:
            for base, quote in TRADING_PAIRS:
                norm_symbol = f"{normalize_symbol(base)}/{normalize_symbol(quote)}"
                ws_price = ws_fetcher.get_latest_price(exchange_id, norm_symbol)
                
                if ws_price and ws_price.bid > 0:
                    # Convert WSPrice to CEXPrice
                    cex_p = CEXPrice(
                        exchange=exchange_id,
                        symbol=norm_symbol,
                        bid=ws_price.bid,
                        ask=ws_price.ask,
                        mid=(ws_price.bid + ws_price.ask) / 2,
                        timestamp=int(ws_price.timestamp * 1000), # Back to ms for consistency
                        volume_24h=None # WS often doesn't stream 24h vol, but arb engine handles None
                    )
                    
                    if norm_symbol not in cex_prices:
                        cex_prices[norm_symbol] = []
                    cex_prices[norm_symbol].append(cex_p)
        
        self._gas_estimates = gas_estimates
        
        # Build price matrix
        price_matrix = self._build_price_matrix(cex_prices, dex_prices)
        
        # Count total pairs
        self._total_pairs_checked = sum(len(sources) for sources in price_matrix.values())
        
        # Find opportunities
        self._opportunities = self._find_opportunities(price_matrix)
        self._last_scan_time = datetime.now()
        
        scan_duration = (self._last_scan_time - scan_start).total_seconds()
        logger.debug(f"Scan completed in {scan_duration:.2f}s, found {len(self._opportunities)} opportunities")
        
        return self._opportunities
    
    async def run_continuous(self, callback=None, on_scan_start=None):
        """
        Run continuous scanning
        
        Args:
            callback: Optional function called with opportunities after each scan
            on_scan_start: Optional function called when a new scan cycle begins
        """
        from config.settings import SCAN_INTERVAL_SECONDS
        
        while True:
            try:
                if on_scan_start:
                    if asyncio.iscoroutinefunction(on_scan_start):
                        await on_scan_start()
                    else:
                        on_scan_start()

                opportunities = await self.scan()
                
                if callback:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(opportunities)
                    else:
                        callback(opportunities)
                
                await asyncio.sleep(SCAN_INTERVAL_SECONDS)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scan error: {e}")
                await asyncio.sleep(5)
    
    @property
    def last_scan_time(self) -> Optional[datetime]:
        return self._last_scan_time
    
    @property
    def total_pairs_checked(self) -> int:
        return self._total_pairs_checked
    
    @property
    def current_opportunities(self) -> list[ArbitrageOpportunity]:
        return self._opportunities


# Global instance
arbitrage_engine = ArbitrageEngine()
