"""
Arbitrage Detection Engine
Finds profitable arbitrage opportunities across CEXs and DEXs
"""
import asyncio
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from config.chains import ChainId
from config.tokens import TRADING_PAIRS, normalize_symbol, ALL_TOKENS
from config.settings import MIN_PROFIT_USD, DEFAULT_TRADE_SIZE_USD, get_profit_level, ProfitLevel
from exchanges.cex.ccxt_fetcher import cex_fetcher, CEXPrice
from exchanges.cex.ws_fetcher import ws_fetcher
from exchanges.dex.aggregator import dex_aggregator, DEXQuote
from core.gas_estimator import gas_estimator, GasEstimate
from core.strategies.triangular import triangular_strategy
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
        self._triangular_opps = [] # New list for triangular
        self._discovered_pairs: list[tuple[str, str]] = []
        self._last_harvest_time: float = 0
    
    async def initialize(self):
        """Initialize all price fetchers"""
        logger.info("[bold blue]Initializing Arbitrage Engine...[/bold blue]")
        
        # Initialize CEX fetcher (REST)
        await cex_fetcher.initialize()
        
        # DYNAMIC HARVESTING: ID all liquid markets before starting WS
        logger.info("[yellow]Performing initial market harvest...[/yellow]")
        top_pairs = cex_fetcher.harvest_all_markets(min_exchanges=2)
        self._discovered_pairs = list(set(top_pairs + TRADING_PAIRS))
        self._last_harvest_time = datetime.now().timestamp()
        
        # Initialize WS fetcher (Real-time) with discovered symbols
        await ws_fetcher.initialize()
        ws_symbols = [f"{normalize_symbol(b)}/{normalize_symbol(q)}" for b, q in self._discovered_pairs]
        # Only watch top 500 pairs via WS to avoid overwhelming connections
        await ws_fetcher.start(ws_symbols[:500])
        
        # Initialize DEX aggregator
        await dex_aggregator.initialize()
        
        # Get initial gas estimates
        self._gas_estimates = await gas_estimator.get_all_gas_estimates()
        
        logger.info("[bold green]Arbitrage Engine ready![/bold green]")
        
    def _update_token_prices(self, cex_prices: dict[str, list[CEXPrice]]):
        """Update global token prices based on fresh CEX data"""
        from config.tokens import CEX_SYMBOL_MAP
        
        # Create a reverse map for easier lookup if needed, 
        # but here we can just iterate known major tokens
        
        # We really only care about major tokens that are used for pricing/routing logic
        # or where approx_price_usd is critical (like ETH, BTC, BNB)
        
        # flatten prices for O(1) lookup
        latest_prices = {}
        for symbol, prices in cex_prices.items():
            # calculate average mid price from reliable exchanges
            valid_mids = [p.mid for p in prices if p.mid > 0]
            if valid_mids:
                avg_price = sum(valid_mids) / len(valid_mids)
                latest_prices[symbol] = avg_price
        
        count = 0
        for token in ALL_TOKENS:
            # Construct possible pairs (e.g. ETH/USDT)
            # We assume USDT is the numeraire
            search_pairs = [
                f"{token.symbol}/USDT",
                f"{token.symbol}/USDC"
            ]
            
            # Check map
            if token.symbol in CEX_SYMBOL_MAP:
                mapped = CEX_SYMBOL_MAP[token.symbol]
                search_pairs.append(f"{mapped}/USDT")
                search_pairs.append(f"{mapped}/USDC")
            
            for pair in search_pairs:
                if pair in latest_prices:
                    token.approx_price_usd = latest_prices[pair]
                    count += 1
                    break
        
        if count > 0:
            logger.debug(f"Updated {count} token prices from CEX data")
    
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
                # Tolerant check for now
                if age > 600:
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
            else:
                cost += self._get_fallback_gas_cost(buy_source.chain)
        
        if sell_source.source_type == "DEX" and sell_source.chain:
            estimate = self._gas_estimates.get(sell_source.chain)
            if estimate:
                cost += estimate.swap_cost_usd
            else:
                cost += self._get_fallback_gas_cost(sell_source.chain)
        
        # CEX trading fees (approximate 0.1% or lower with VIP)
        if buy_source.source_type == "CEX":
            cost += DEFAULT_TRADE_SIZE_USD * 0.001
        if sell_source.source_type == "CEX":
            cost += DEFAULT_TRADE_SIZE_USD * 0.001
            
        return cost

    def _get_fallback_gas_cost(self, chain_id: ChainId) -> float:
        """Conservative fallback gas costs if estimation fails"""
        # L1s are expensive, L2s are cheap but not zero
        if chain_id == ChainId.ETHEREUM:
            return 25.0 # High fallback for ETH
        elif chain_id == ChainId.BSC:
            return 0.30
        elif chain_id in [ChainId.ARBITRUM, ChainId.OPTIMISM, ChainId.BASE, ChainId.LINEA, ChainId.SCROLL, ChainId.ZKSYNC]:
            return 0.50 # L2 execution + L1 data blob estimate
        elif chain_id in [ChainId.POLYGON, ChainId.AVALANCHE, ChainId.FANTOM]:
            return 0.10
        return 0.20 # Default other

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
        
        # 1. DYNAMIC HARVESTING (Every 10 minutes or first run)
        now_ts = datetime.now().timestamp()
        if not self._discovered_pairs or now_ts - self._last_harvest_time > 600:
            logger.info("Harvesting all liquid markets dynamically...")
            cex_pairs = cex_fetcher.harvest_all_markets(min_exchanges=2)
            
            # Combine with hardcoded ones to ensure we don't miss core tokens
            combined = list(set(cex_pairs + TRADING_PAIRS))
            self._discovered_pairs = combined
            self._last_harvest_time = now_ts
            logger.info(f"Scanning {len(self._discovered_pairs)} unique pairs across all markets")

        # 2. IDENTIFY WS EXCHANGES
        ws_active_exchanges = list(ws_fetcher._exchanges.keys())
        
        # 3. FETCH REST + DEX + GAS
        # Optimization: Fetch DEX only for pairs that have Token mappings
        # To avoid giant multicalls for assets we don't have addresses for
        dex_pairs = []
        from config.tokens import ALL_TOKENS, normalize_symbol
        # Build token symbol map for speed
        token_map = {t.symbol: t for t in ALL_TOKENS}
        
        for base, quote in self._discovered_pairs:
            # Check if we have both tokens in our DEX config
            if base in token_map and quote in token_map:
                dex_pairs.append((base, quote))

        cex_task = cex_fetcher.fetch_all_prices(self._discovered_pairs, exclude_exchanges=ws_active_exchanges)
        dex_task = dex_aggregator.fetch_all_prices(dex_pairs)
        gas_task = gas_estimator.get_all_gas_estimates()
        
        cex_prices, dex_prices, gas_estimates = await asyncio.gather(
            cex_task, dex_task, gas_task
        )
        
        # 4. MERGE WS PRICES
        for exchange_id in ws_active_exchanges:
            for base, quote in self._discovered_pairs:
                norm_symbol = f"{normalize_symbol(base)}/{normalize_symbol(quote)}"
                ws_price = ws_fetcher.get_latest_price(exchange_id, norm_symbol)
                
                if ws_price and ws_price.bid > 0:
                    cex_p = CEXPrice(
                        exchange=exchange_id,
                        symbol=norm_symbol,
                        bid=ws_price.bid,
                        ask=ws_price.ask,
                        mid=(ws_price.bid + ws_price.ask) / 2,
                        timestamp=int(ws_price.timestamp * 1000),
                        volume_24h=None
                    )
                    
                    if norm_symbol not in cex_prices:
                        cex_prices[norm_symbol] = []
                    cex_prices[norm_symbol].append(cex_p)
        
        self._gas_estimates = gas_estimates
        
        # 4. UPDATE DYNAMIC PRICES
        self._update_token_prices(cex_prices)
        
        # Build price matrix
        price_matrix = self._build_price_matrix(cex_prices, dex_prices)
        
        # 5. FIND TRIANGULAR OPPORTUNITIES
        self._triangular_opps = triangular_strategy.find_opportunities(cex_prices)
        if self._triangular_opps:
            logger.info(f"[magenta]Found {len(self._triangular_opps)} Triangular Opportunities![/magenta]")
            for opp in self._triangular_opps[:2]:
                logger.info(f"  - {opp.exchange}: {' -> '.join(opp.symbol_path)} | Profit: {opp.expected_profit_pct:.2f}%")

        # Count total pairs
        self._total_pairs_checked = sum(len(sources) for sources in price_matrix.values())
        
        # Find opportunities
        self._opportunities = self._find_opportunities(price_matrix)
        self._last_scan_time = datetime.now()
        
        scan_duration = (self._last_scan_time - scan_start).total_seconds()
        logger.debug(f"Scan completed in {scan_duration:.2f}s, found {len(self._opportunities)} cross-source opportunities")
        
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
